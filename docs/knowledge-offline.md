# 知识库隐私与离线性说明

**中文** | [English](#knowledge-base-privacy--offline-guarantee)

---

## 知识库是完全本地化的，数据不会上传到云端

SkillAgent 的个人知识库在**嵌入（向量化）和存储**两个环节均完全在本地完成，不会将您的私密文件内容发送给任何云端服务。

---

## 技术实现细节

### 向量化（Embedding）

向量化是将文本转换为数值向量（用于语义检索）的过程。

| 项目 | 详情 |
|------|------|
| 使用模型 | `all-MiniLM-L6-v2`（通过 ChromaDB 内置 ONNX Runtime 在本地运行） |
| 运行方式 | **纯本地推理**，基于 ONNX Runtime，无需 GPU |
| 模型缓存位置 | `~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/` |
| 首次使用 | 首次导入文档时自动下载模型文件（约 23 MB），之后完全离线 |
| 网络请求 | 模型下载完成后，向量化过程**零网络请求** |

### 向量数据库存储

| 项目 | 详情 |
|------|------|
| 数据库引擎 | [ChromaDB](https://www.trychroma.com/) `PersistentClient`（纯本地） |
| 数据存储位置 | `./data/chromadb/`（项目目录内，仅您本机可访问） |
| 匿名遥测 | 已显式禁用（`anonymized_telemetry=False`） |
| 云端同步 | **不存在**，无任何自动上传机制 |

见 [`knowledge/vector_store.py`](../knowledge/vector_store.py)：

```python
self._client = chromadb.PersistentClient(
    path=persist_directory,
    settings=Settings(anonymized_telemetry=False),
)
```

---

## 数据流分析：哪些内容会发送给云端 LLM？

### 导入文档时

```
您的文件（Excel / PDF / EML / ...）
    │
    ▼
[本地] 文本提取（pypdf / openpyxl / email 模块）
    │
    ▼
[本地] ONNX 向量化（all-MiniLM-L6-v2）
    │
    ▼
[本地] 存入 ChromaDB（./data/chromadb/）
    │
    ✗  此步骤不产生任何网络请求
```

**结论：导入文档时，文件内容完全不离开本机。**

---

### 提问时

```
用户提问："合同里的付款条款是什么？"
    │
    ▼
[本地] ONNX 向量化查询文本
    │
    ▼
[本地] ChromaDB 语义搜索，返回 top-5 匹配片段
       每个片段最多 200 字符（见 knowledge_skill.py）
    │
    ▼
[云端] 发给 LLM 的 Prompt 仅包含：
       • 您的提问
       • 最多 5 条 × 200 字符 = 约 1000 字符的知识摘要
    │
    ▼
LLM 返回回答
```

**结论：每次提问，LLM 只收到语义最相关的极小片段（约 1000 字符），原始文件的完整内容永远不会发送给云端 LLM。**

---

## 常见问题

**Q：把整个 Excel 存入知识库后，LLM 能看到所有行吗？**

不能。LLM 每次只接收到与您当前问题语义最相关的片段（200 字符/条，最多 5 条）。Excel 的其余内容仍存放在本地 ChromaDB 中，不会主动推送给 LLM。

**Q：`data/chromadb/` 目录下的文件能直接被他人读取吗？**

该目录存放在项目文件夹内，访问权限与您其他本地文件相同，与任何云端无关。如需加密，可配合操作系统的文件加密功能（如 BitLocker）使用。

**Q：卸载项目后数据会消失吗？**

删除 `./data/chromadb/` 目录即可彻底删除所有知识库数据，无需联系任何服务提供商。

**Q：首次下载的 ONNX 模型去哪了？**

位于 `~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/`，可手动删除。删除后下次导入文档时会重新下载（需要网络）。

---

---

# Knowledge Base Privacy & Offline Guarantee

[中文](#知识库隐私与离线性说明) | **English**

---

## The knowledge base is fully local — your data never leaves your machine

SkillAgent's personal knowledge base performs both **embedding (vectorisation)** and **storage** entirely on your local machine. Your private file contents are never sent to any cloud service.

---

## Technical Details

### Embedding (Vectorisation)

Embedding converts text into numerical vectors used for semantic search.

| Item | Detail |
|------|--------|
| Model | `all-MiniLM-L6-v2` (runs locally via ChromaDB's built-in ONNX Runtime) |
| Execution | **Fully local inference** — ONNX Runtime, no GPU required |
| Model cache | `~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/` |
| First use | Model is auto-downloaded (~23 MB) on first import; fully offline afterward |
| Network | After the one-time download, embedding makes **zero network requests** |

### Vector Database Storage

| Item | Detail |
|------|--------|
| Engine | [ChromaDB](https://www.trychroma.com/) `PersistentClient` (local only) |
| Data location | `./data/chromadb/` (inside your project folder — only your machine can access it) |
| Anonymous telemetry | Explicitly disabled (`anonymized_telemetry=False`) |
| Cloud sync | **None** — no automatic upload mechanism exists |

See [`knowledge/vector_store.py`](../knowledge/vector_store.py):

```python
self._client = chromadb.PersistentClient(
    path=persist_directory,
    settings=Settings(anonymized_telemetry=False),
)
```

---

## Data Flow: What Actually Goes to the Cloud LLM?

### When importing a document

```
Your file (Excel / PDF / EML / ...)
    │
    ▼
[Local] Text extraction (pypdf / openpyxl / email module)
    │
    ▼
[Local] ONNX vectorisation (all-MiniLM-L6-v2)
    │
    ▼
[Local] Saved to ChromaDB (./data/chromadb/)
    │
    ✗  No network request at any step
```

**Result: When importing a document, file contents never leave your machine.**

---

### When asking a question

```
User question: "What are the payment terms in the contract?"
    │
    ▼
[Local] ONNX vectorises the query
    │
    ▼
[Local] ChromaDB semantic search → top-5 matched snippets
        Each snippet is at most 200 characters (see knowledge_skill.py)
    │
    ▼
[Cloud] Prompt sent to LLM contains only:
        • Your question
        • Up to 5 × 200 chars = ~1,000 chars of knowledge summaries
    │
    ▼
LLM returns its answer
```

**Result: For every question, the LLM only receives the most semantically relevant micro-snippets (~1,000 chars total). The full content of your original files is never sent to the cloud LLM.**

---

## FAQ

**Q: After importing a large Excel file, can the LLM see all rows?**

No. The LLM only receives the snippets most semantically relevant to your current question (up to 200 chars each, at most 5 snippets). The rest of the Excel content stays in the local ChromaDB and is never proactively pushed to the LLM.

**Q: Can others read the files in `data/chromadb/`?**

The directory lives inside your project folder and has the same access controls as any other local file. It has no connection to any cloud service. For encryption, you can combine it with OS-level encryption (e.g. BitLocker on Windows, FileVault on macOS).

**Q: Will my data disappear if I uninstall the project?**

Deleting `./data/chromadb/` completely removes all knowledge base data. No cloud service provider needs to be contacted.

**Q: Where is the one-time ONNX model download stored?**

At `~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/`. You can delete it manually. If deleted, it will be re-downloaded the next time you import a document (requires internet).
