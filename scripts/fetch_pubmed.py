#!/usr/bin/env python3
"""Fetch recent English PubMed literature related to peritoneal adhesions."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
QUERY = """(
  "peritoneal adhesion"[Title/Abstract] OR "peritoneal adhesions"[Title/Abstract]
  OR "peritoneal adhesion formation"[Title/Abstract]
  OR "intraperitoneal adhesion"[Title/Abstract] OR "intraperitoneal adhesions"[Title/Abstract]
  OR "abdominal adhesion"[Title/Abstract] OR "abdominal adhesions"[Title/Abstract]
  OR "intra-abdominal adhesion"[Title/Abstract] OR "intra-abdominal adhesions"[Title/Abstract]
  OR "intraabdominal adhesion"[Title/Abstract] OR "intraabdominal adhesions"[Title/Abstract]
  OR "postoperative abdominal adhesion"[Title/Abstract] OR "postoperative abdominal adhesions"[Title/Abstract]
  OR "postoperative peritoneal adhesion"[Title/Abstract] OR "postoperative peritoneal adhesions"[Title/Abstract]
  OR ("Tissue Adhesions"[MeSH Major Topic] AND "Peritoneum"[MeSH Major Topic])
) AND english[Language]"""

TOPIC_RULES = {
    "Prevention": (r"\bprevent", r"\banti-adhesion", r"\bbarrier", r"\bprophylaxis"),
    "Biomaterials": (r"\bhydrogel", r"\bfilm\b", r"\bmembrane", r"\bbiomaterial", r"\bscaffold", r"\bnanoparticle"),
    "Mechanism": (r"\bfibrosis", r"\bfibroblast", r"\bmesothelial", r"\binflammation", r"\bpathogenesis", r"\bmechanism"),
    "Surgery": (r"\bsurg", r"\blaparoscop", r"\boperation", r"\boperative"),
    "Animal Study": (r"\brats?\b", r"\bmice\b", r"\bmouse\b", r"\brabbits?\b", r"\banimal model"),
    "Clinical Study": (r"\bpatients?\b", r"\bclinical\b", r"\brandomi[sz]ed", r"\bcohort\b", r"\btrial\b"),
}


def request(endpoint: str, params: dict[str, str]) -> bytes:
    params["tool"] = "peritoneal_adhesion_research_radar"
    email = os.getenv("NCBI_EMAIL")
    api_key = os.getenv("NCBI_API_KEY")
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key
    url = BASE_URL + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read()


def text_content(element: ET.Element | None) -> str:
    if element is None:
        return ""
    value = "".join(element.itertext())
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def pub_date(article: ET.Element) -> tuple[str, str]:
    date = article.find("./MedlineCitation/Article/Journal/JournalIssue/PubDate")
    if date is None:
        return "", ""
    year = text_content(date.find("Year"))
    month = text_content(date.find("Month"))
    day = text_content(date.find("Day"))
    medline_date = text_content(date.find("MedlineDate"))
    if not year and medline_date:
        year_match = re.search(r"\d{4}", medline_date)
        year = year_match.group(0) if year_match else ""
        return medline_date, year
    display = " ".join(value for value in (year, month, day) if value)
    return display, year


def identify_topics(title: str, abstract: str, publication_types: list[str]) -> list[str]:
    searchable = f"{title} {abstract} {' '.join(publication_types)}".lower()
    topics = [
        topic for topic, patterns in TOPIC_RULES.items()
        if any(re.search(pattern, searchable) for pattern in patterns)
    ]
    return topics or ["General"]


def parse_article(article: ET.Element) -> dict[str, object]:
    citation = article.find("./MedlineCitation")
    pmid = text_content(citation.find("PMID") if citation is not None else None)
    title = text_content(article.find("./MedlineCitation/Article/ArticleTitle"))
    abstract_parts = [
        text_content(section)
        for section in article.findall("./MedlineCitation/Article/Abstract/AbstractText")
    ]
    abstract = " ".join(part for part in abstract_parts if part)
    journal = text_content(article.find("./MedlineCitation/Article/Journal/Title"))
    authors = []
    for author in article.findall("./MedlineCitation/Article/AuthorList/Author"):
        collective = text_content(author.find("CollectiveName"))
        family = text_content(author.find("LastName"))
        initials = text_content(author.find("Initials"))
        author_name = collective or " ".join(part for part in (family, initials) if part)
        if author_name:
            authors.append(author_name)
    publication_types = [
        text_content(node)
        for node in article.findall("./MedlineCitation/Article/PublicationTypeList/PublicationType")
        if text_content(node)
    ]
    doi = ""
    for identifier in article.findall("./PubmedData/ArticleIdList/ArticleId"):
        if identifier.attrib.get("IdType") == "doi":
            doi = text_content(identifier)
            break
    publication_date, year = pub_date(article)
    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "journal": journal,
        "authors": authors,
        "publicationTypes": publication_types,
        "publicationDate": publication_date,
        "year": year,
        "doi": doi,
        "pubmedUrl": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "topics": identify_topics(title, abstract, publication_types),
    }


def fetch_articles(limit: int) -> list[dict[str, object]]:
    search_data = request("esearch.fcgi", {
        "db": "pubmed",
        "term": QUERY,
        "retmode": "json",
        "retmax": str(limit),
        "sort": "pub_date",
    })
    ids = json.loads(search_data)["esearchresult"]["idlist"]
    if not ids:
        return []
    time.sleep(0.12)
    fetched = request("efetch.fcgi", {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml",
    })
    root = ET.fromstring(fetched)
    return [parse_article(article) for article in root.findall("./PubmedArticle")]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=120, help="Number of recent records to retain")
    parser.add_argument("--output", type=Path, default=Path("data/articles.json"))
    args = parser.parse_args()
    articles = fetch_articles(args.limit)
    payload = {
        "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "PubMed",
        "language": "English",
        "query": QUERY,
        "articles": articles,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(articles)} articles to {args.output}")


if __name__ == "__main__":
    main()
