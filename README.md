# 腹膜粘连英文文献追踪站

一个面向医学研究生的静态文献仪表盘，每天自动检索 PubMed 中最新的腹膜粘连相关英文研究，并展示标题、摘要、期刊、文章类型、PMID/DOI 及主题标签。

## 功能

- 以英文 PubMed 记录为主，覆盖 `peritoneal adhesion`、`postoperative adhesion`、`intra-abdominal adhesion` 及相关 MeSH 检索组合。
- 支持按题名/摘要/作者/期刊搜索，并按年份、文章类型与研究方向过滤。
- 每天北京时间 `06:10` 由 GitHub Actions 自动更新最近 120 条记录并部署网站。
- 网站为纯静态文件，可免费托管在 GitHub Pages。

## 本地运行

生成最新数据：

```bash
python3 scripts/fetch_pubmed.py --limit 120
```

启动本地静态服务器：

```bash
python3 -m http.server 8000
```

浏览器访问 `http://localhost:8000`。

## 部署到 GitHub Pages

1. 将仓库推送至 GitHub，默认分支使用 `main`。
2. 在仓库 `Settings > Pages > Build and deployment` 中将 Source 选择为 `GitHub Actions`。
3. 在 `Settings > Secrets and variables > Actions` 新建 secret `NCBI_EMAIL`，填写用于 NCBI 请求标识的邮箱。
4. 可选：申请 NCBI API Key 后再新增 secret `NCBI_API_KEY`，以支持更高请求额度。
5. 打开 `Actions`，手动运行一次 `Update Literature and Deploy Site`，随后网站会每天自动更新。

## 数据来源与声明

数据通过 NCBI 官方 [E-utilities API](https://www.ncbi.nlm.nih.gov/books/NBK25501/) 查询 PubMed 获得。本网站用于科研追踪与阅读入口整理，不替代全文评价、系统综述流程或临床决策依据。
