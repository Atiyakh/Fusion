// src/App.jsx
import './App.css';
import NotebookCell from './components/NotebookCell/NotebookCell/NotebookCell.jsx';
import NotebookCellToolBar from "./components/NotebookCellToolBar/NotebookCellToolBar.jsx";
import { CellAreaProvider } from './contexts/CellAreaContext.jsx';
import { UIComponentsProvider } from './contexts/UIComponentsContext.jsx';
import { TabBarProvider } from './contexts/TabBarContext.jsx';
import ProjectFileTree from './components/ProjectFileTree/ProjectFileTree.jsx';
import NotebookStatusBar from './components/NotebookStatusBar/NotebookStatusBar.jsx';
import ActivityBar from './components/ActivityBar/ActivityBar.jsx';
import TabBar from './components/TabBar/TabBar.jsx';
import { useRef  } from 'react';
// import MarkdownCell from './components/MarkdownCell.jsx';
import 'focus-visible';

// placeholder data
const cells = {
  cellNo1: {
    initialValue: `# Imports
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# Load + Prep Data
df = pd.read_csv("housing.csv")

# quick sanity check (because blindly trusting datasets is how you get clowned)
df = df.dropna()

features = ["sqft", "bedrooms", "bathrooms", "age"]
target = "price"`,
    cellTitle: "Data Load + Cleanup"
  },
  cellNo2: {
    initialValue: `X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train Model
model = RandomForestRegressor(
    n_estimators=300,
    max_depth=12,
    random_state=42,
    n_jobs=-1,
)

model.fit(X_train, y_train)`,
    cellTitle: "Train Model"
  },
  cellNo3: {
    initialValue: `# Evaluate (aka find out if you cooked or fumbled)
preds = model.predict(X_test)

mae = mean_absolute_error(y_test, preds)
r2 = r2_score(y_test, preds)

print(f"MAE: {mae:,.2f}")
print(f"R²:  {r2:.3f}")

# Feature importance (the tea)
importances = pd.DataFrame(
    {"feature": features, "importance": model.feature_importances_}
).sort_values("importance", ascending=False)

importances`,
    cellTitle: "Performance Check + Feature Weights"
  }
};
const directory = {
  name: "my_data_project",
  type: "folder",
  children: [
    {
      name: "src",
      type: "folder",
      children: [
        { name: "main.py", type: "file" },
        { name: "train_model.py", type: "file" },
        { name: "predict.py", type: "file" },
        {
          name: "data_processing",
          type: "folder",
          children: [
            { name: "load_data.py", type: "file" },
            { name: "clean_data.py", type: "file" },
            { name: "feature_engineering.py", type: "file" },
            { name: "transformers.py", type: "file" }
          ]
        },
        {
          name: "models",
          type: "folder",
          children: [
            { name: "model_utils.py", type: "file" },
            { name: "linear_regression.py", type: "file" },
            { name: "random_forest.py", type: "file" },
            { name: "neural_net.py", type: "file" }
          ]
        },
        {
          name: "visualizations",
          type: "folder",
          children: [
            { name: "plot_helpers.py", type: "file" },
            { name: "eda_plots.ipynb", type: "file" }
          ]
        },
        {
          name: "utils",
          type: "folder",
          children: [
            { name: "logger.py", type: "file" },
            { name: "config.py", type: "file" },
            { name: "metrics.py", type: "file" }
          ]
        }
      ]
    },
    {
      name: "notebooks",
      type: "folder",
      children: [
        { name: "01_data_exploration.ipynb", type: "file" },
        { name: "02_feature_engineering.ipynb", type: "file" },
        { name: "03_model_training.ipynb", type: "file" },
        { name: "04_evaluation.ipynb", type: "file" }
      ]
    },
    {
      name: "data",
      type: "folder",
      children: [
        {
          name: "raw",
          type: "folder",
          children: [
            { name: "customers.csv", type: "file" },
            { name: "transactions.csv", type: "file" },
            { name: "products.csv", type: "file" },
            { name: "lookup_tables.xlsx", type: "file" }
          ]
        },
        {
          name: "processed",
          type: "folder",
          children: [
            { name: "train_features.parquet", type: "file" },
            { name: "test_features.parquet", type: "file" },
            { name: "labels.npy", type: "file" }
          ]
        }
      ]
    },
    {
      name: "models",
      type: "folder",
      children: [
        { name: "linear_regression.pkl", type: "file" },
        { name: "random_forest.joblib", type: "file" },
        { name: "neural_net.pt", type: "file" },
        { name: "experiment_tracking.csv", type: "file" }
      ]
    },
    {
      name: "configs",
      type: "folder",
      children: [
        { name: "default.yaml", type: "file" },
        { name: "paths.json", type: "file" },
        { name: "hyperparameters.toml", type: "file" }
      ]
    },
    {
      name: "scripts",
      type: "folder",
      children: [
        { name: "run_pipeline.sh", type: "file" },
        { name: "submit_job.py", type: "file" },
        { name: "evaluate_results.py", type: "file" }
      ]
    },
    {
      name: "logs",
      type: "folder",
      children: [
        { name: "training.log", type: "file" },
        { name: "pipeline.log", type: "file" }
      ]
    },
    {
      name: "tests",
      type: "folder",
      children: [
        { name: "test_data_processing.py", type: "file" },
        { name: "test_models.py", type: "file" },
        { name: "test_utils.py", type: "file" }
      ]
    },
    { name: "README.md", type: "file" },
    { name: ".gitignore", type: "file" },
    { name: "requirements.txt", type: "file" },
    { name: "environment.yml", type: "file" },
    { name: "setup.py", type: "file" }
  ]
};

export default function App() {
  const tabBarRef = useRef(null);
  return (
    <>
      <TabBarProvider>
        <UIComponentsProvider>
            <div className='notebook-workspace'>
              <ActivityBar />
              <ProjectFileTree projectData={{ projectName: "PROJECT FILES", directory }} />
              <div className='notebook-editor-area'>
                <TabBar ref={tabBarRef} />
                <CellAreaProvider>
                  <div className='cell-area'>
                    <NotebookCell cellData={cells.cellNo1}/>
                    <NotebookCellToolBar />

                    <NotebookCell cellData={cells.cellNo2}/>
                    <NotebookCellToolBar />

                    <NotebookCell cellData={cells.cellNo3}/>
                    <NotebookCellToolBar />
                  </div>
                </CellAreaProvider>
              </div>
            </div>
            <NotebookStatusBar />
        </UIComponentsProvider>
      </TabBarProvider>
    </>
  );
}
