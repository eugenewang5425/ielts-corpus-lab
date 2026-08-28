<a id="readme-zh"></a>

# IELTS Corpus Lab 公共镜像

**中文** · [English](#readme-en)

IELTS Corpus Lab 的静态公开镜像，提供可追溯的雅思语料统计与练习界面。网站以中文为主要语言，公开数据通过 GitHub 进行版本管理，并由 GitHub Pages 自动部署。

访问网站：[IELTS Corpus Lab](https://eugenewang5425.github.io/ielts-corpus-lab/)

## 项目包含什么

- 听、说、读、写四科词频统计，并过滤 `a`、`to` 等基础停用词。
- 总体词频与 2021—2026 近五年词频；词表收录所有达到文档频率门槛的词元，不设置 Top 750 截断。
- 阅读与听力高频词块，包括人工整理的核心词块及满足跨文档、跨来源条件的完整自动扩展结果，不设置 Top 450 抽样上限。
- 写作 Task 1 / Task 2 的分类、题目、答题思路、模板、词汇、原创范文与自检内容。
- 按 Part 1 / Part 2 / Part 3 整合的口语主题、去重问题、答题思路、模板与示范回答；每道来源题保留可追溯的来源引用。
- 来源审计页面目前展示八个来源层、32 张聚合来源卡；Cambridge IELTS Academic 4—21 按 18 册分别列出。

## 数据与版权边界

本仓库不会重新发布 Cambridge IELTS 的原始文章、音频、图片、答案或第三方范文。Cambridge IELTS Academic 4—21 仅在本地私有流程中提取为分段缓存，再生成公开的聚合统计；受版权保护的原文不会进入 Git。

公开数据包括四科聚合词频、阅读/听力词块、写作分类、合并后的口语主题、去重且带来源的问题，以及本站原创练习内容。原创范文会明确标注为“本站原创练习”，不冒充 IELTS 官方范文。

`data/manifest.json` 是不缓存的版本入口，前端会据此加载同一版本的五个 JSON 数据文件。GitHub 在当前网络兼容方案中充当公开、带版本记录的只读数据库；更新 `main` 并完成 Pages 构建后，访客即可读取最新数据。

## 刷新语料库

在仓库根目录依次运行：

```powershell
python scripts/extract_local_speaking.py
python scripts/extract_cambridge_sections.py
python scripts/build_corpus_snapshot.py
python scripts/build_merged_speaking_bank.py
python scripts/build_lr_chunks.py
python scripts/generate_question_bank.py
python scripts/validate_public_data.py
```

Cambridge 与本地口语提取缓存位于仓库外的 `outputs/ielts-corpus-build`。口语构建会把每条来源记录拆成独立 Part 问题，映射到统一主题分类，合并文本相同的问题，同时保留全部来源引用。2026 年 9—12 月本地资料会被明确标为“未来预测”，不会冒充已经核实的当期题库。

阅读/听力词块构建会保留人工核心条目和手工索引条目，并仅在二元或三元词组跨多个文档、且至少出现在两个来源集合时纳入自动扩展。自动发现的条目会标注为学习索引，不会冒充人工翻译。

## 验证与发布

`scripts/validate_public_data.py` 会检查数据版本一致性、题库结构、来源引用、词块质量规则、版权边界及必要字段。推送到 `main` 后，由 GitHub Actions 执行验证并发布 GitHub Pages。

---

<a id="readme-en"></a>

# IELTS Corpus Lab Public Mirror

[中文](#readme-zh) · **English**

IELTS Corpus Lab is a static public mirror that provides traceable IELTS corpus statistics and practice materials. Chinese is the primary interface language. Public data is versioned on GitHub and deployed automatically through GitHub Pages.

Visit the site: [IELTS Corpus Lab](https://eugenewang5425.github.io/ielts-corpus-lab/)

## What is included

- Word-frequency statistics for Listening, Speaking, Reading, and Writing, with elementary stop words such as `a` and `to` excluded.
- Overall and 2021—2026 recent-frequency views. Every lemma that passes the documented document-frequency threshold is published, with no Top 750 cap.
- Reading and Listening chunks, combining a curated core with the complete automatically discovered set that meets cross-document and cross-source requirements; there is no Top 450 sampling cap.
- Writing Task 1 and Task 2 categories, prompts, planning guidance, templates, vocabulary, original model responses, and self-check activities.
- Speaking topics organized across Part 1, Part 2, and Part 3, with deduplicated questions, planning guidance, templates, sample answers, and traceable per-question source references.
- A source audit covering eight source layers and 32 aggregate source cards. Cambridge IELTS Academic 4—21 is listed as 18 separate volume sources.

## Data and copyright boundaries

This repository does not republish Cambridge IELTS passages, audio, images, answer keys, or third-party model answers. Cambridge IELTS Academic 4—21 is processed only into private local section caches and then converted into public aggregate statistics. Copyrighted raw text never enters Git.

The public dataset contains four-skill aggregate word statistics, Reading and Listening chunks, writing facets, merged speaking topics, deduplicated attributed source questions, and original practice content. Original model responses are explicitly labelled as original site practice and are not presented as official IELTS answers.

`data/manifest.json` is the uncached version pointer. The client uses it to load the matching five-file JSON snapshot. GitHub serves as the public, versioned, read-only database for this network-compatible deployment. After `main` is updated and the Pages build completes, visitors receive the latest dataset.

## Refreshing the corpus

Run the following commands from the repository root:

```powershell
python scripts/extract_local_speaking.py
python scripts/extract_cambridge_sections.py
python scripts/build_corpus_snapshot.py
python scripts/build_merged_speaking_bank.py
python scripts/build_lr_chunks.py
python scripts/generate_question_bank.py
python scripts/validate_public_data.py
```

The Cambridge and local speaking extraction caches live outside the repository under `outputs/ielts-corpus-build`. The speaking build splits each source record into individual Part questions, maps them to a controlled topic taxonomy, merges identical question text, and preserves every source reference. Local material for September—December 2026 is explicitly labelled as an upcoming prediction rather than a verified current question bank.

The Reading and Listening chunk build retains curated core and manually indexed entries. It adds two- and three-word sequences only when they recur across documents and appear in at least two source collections. Automatically discovered entries are labelled as functional study indexes rather than human translations.

## Validation and deployment

`scripts/validate_public_data.py` checks snapshot version consistency, question-bank structure, source references, chunk-quality rules, copyright boundaries, and required fields. After a push to `main`, GitHub Actions validates the data and deploys the site to GitHub Pages.

---

## 支持项目 / Support the project

如果这个项目对你有帮助，可以自愿通过微信赞赏支持语料整理、数据核验和网站维护。<br>
If this project helps you, you may voluntarily support its corpus curation, data verification, and maintenance through WeChat.

<p align="center">
  <a href="assets/wechat-reward.jpg">
    <img src="assets/wechat-reward.jpg" alt="微信赞赏码 / WeChat reward code" width="380">
  </a>
</p>

<p align="center">微信扫码赞赏 · 点击图片查看原图 · 感谢支持 / Scan with WeChat · Open the image for full size · Thank you</p>
