# ⚡ Fusion (A Local-First Data Science IDE and Data Modeling Env)

> A modern, open-source data science IDE that fuses runtime introspection, hybrid static/dynamic analysis, AI tooling, embedded notebook version control, and native database/cloud integrations while remaining 100% backward compatible with Jupyter notebooks.

---

## 🚀 Why Fusion?

Jupyter notebooks power modern data science, but they were never designed for:

- Real version control
- Large projects with multiple branches
- Database and cloud-native workflows
- Fast, contextual AI tooling
- Reliable object inspection and visualization
- Professional developer ergonomics

It's not just a better notebook.  
It's a **modern data science workstation.**

---

## ✨ Key Highlights

- 🧠 **Hybrid static + dynamic inspection**  
  Hover any DataFrame, model, array, or object to see real runtime stats, previews, and plots.

- 🔎 **Interactive hover visualizations**  
  Inline `df.head()`, `describe()`, `info()`, and small seaborn/plotly plots.

- 🤖 **AI-native workflows**  
  Project-aware refactoring & explanation via Gemini CLI + unlimited Codeium completions.

- 🗄️ **Database UI cells**  
  Browse schemas, ER diagrams, run SQL, and convert results to pandas (inside a cell).

- ☁️ **S3 / object storage UI cells**  
  Browse buckets, lazy-load large objects, and stream data directly into your kernel.

- 🕒 **Embedded notebook version control**  
  Cell-level diffs, branching, and time travel powered by SQLite inside the notebook.

- 🧩 **100% Jupyter compatible**  
  UI features are overlays. exported notebooks run in standard Jupyter.

- ⚡ **Local-first & fast**  
  React frontend, local kernel execution, no mandatory cloud dependency.

---

## 🖥️ Screenshots

<p align="center">
  <img src="https://raw.githubusercontent.com/Atiyakh/Fusion/refs/heads/main/screenshots/Screenshot%202025-12-06%20075527.png">
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/Atiyakh/Fusion/refs/heads/main/screenshots/Screenshot%202025-12-05%20092113.png">
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/Atiyakh/Fusion/refs/heads/main/screenshots/Screenshot%202025-12-05%20092052.png">
</p>

- Notebook editor + tabs  
- Hover inspector with plots  
- Database UI cell  
- S3 UI cell  
- Version history / time travel UI  

---

## 🏗️ Architecture Overview

### Frontend
- React-based UI
- Local-first hosting
- Modular plugin system for inspectors, connectors, and AI tools

### Kernel + Language Server
- Pyright language server extended to query the live kernel
- Hybrid static + runtime inspection for real object metadata

### AI Stack
- **Gemini CLI** for project-level reasoning, refactors, and explanations
- **Codeium** for unlimited, contextual code completions

### Notebook Version Control
- Embedded SQLite database stored in `.ipynb` metadata
- Cell-level diff tracking
- Branch-aware linear histories
- Periodic compact checkpoints for fast reconstruction
- Deterministic replay and time travel

### Data Connectors
- Database UI cells (Postgres, MySQL, Snowflake, SQLite, etc.)
- S3-compatible object storage UI cells (AWS, MinIO, etc.)

---

## 🔬 Hybrid Runtime Inspection (How It Works)

Fusion rewires Pyright to consult the live kernel for inspectable objects:

On hover, the IDE can fetch:
- `df.head()`
- `df.describe()`
- `df.info()`
- shape, dtypes, memory usage
- small inline plots (histograms, boxplots, etc.)
- model metadata and parameters

This replaces static guessing with **real runtime truth.**

---

## 🗄️ Database UI Cells

Turn any cell into a full database workspace:

- Connect to relational databases
- Browse schemas and tables
- View ER diagrams
- Scroll table previews
- Run SQL
- Convert query results to pandas DataFrames

All UI actions generate real Python code underneath for full compatibility.

---

## ☁️ S3 / Object Storage UI Cells

Native UI for S3-compatible storage:

- Browse buckets and folders
- Lazy-load large objects
- Load small objects directly into RAM
- Stream data into pandas
- Track mounted/loaded objects

Like a cloud file manager inside your notebook.

---

## 🕒 Notebook Version Control (No Git Required)

Fusion includes a built-in notebook VCS:

### Features
- [experimental] Cell-level diffs (create, edit, delete, move, metadata)
- Virtual branches
- Time travel per cell or full notebook
- Deterministic snapshot reconstruction
- SQLite-backed history stored inside the notebook

### How It Works (High Level)
- Every atomic notebook action is logged as a diff entry
- Diffs are grouped by `branch_id`
- Periodic checkpoints store compact snapshots of cell order + code
- Snapshot reconstruction = nearest checkpoint + replay remaining diffs

### Why This Matters
- No JSON merge conflicts
- No broken notebooks
- No external Git required
- Full portability: notebook + history in one file

---

### Prerequisites
- Node.js (>= 18)
- Python (>= 3.9)
- A local Python kernel environment

---

### License
licensed under the **MIT License**.
