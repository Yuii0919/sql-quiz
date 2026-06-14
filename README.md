# SQL 線上練習題

從四份試卷（RTFD）提取的 SQL 資料庫選擇題，適合手機、平板在搭車時練習。

## 功能

- 52 道去重後的題目（四份試卷合併，自動跳過重複題）
- 隨機 / 依序練習模式
- 手機、平板響應式介面
- 本地儲存練習進度
- 支援深色模式

## 本地預覽

```bash
cd sql-quiz
python3 -m http.server 8080
```

瀏覽器開啟 http://localhost:8080

## 部署到 GitHub Pages

1. 在 GitHub 建立新 repository（例如 `sql-quiz`）

2. 上傳此資料夾內所有檔案：

```bash
cd sql-quiz
git init
git add .
git commit -m "Add SQL practice quiz"
git branch -M main
git remote add origin https://github.com/你的帳號/sql-quiz.git
git push -u origin main
```

3. 到 repo **Settings → Pages**：
   - Source 選 **GitHub Actions**
   - 推送後會自動部署

4. 完成後網址為：
   `https://你的帳號.github.io/sql-quiz/`

## 更新題庫

若修改了 RTFD 來源檔，重新執行：

```bash
python3 scripts/build_questions.py
```

## 檔案結構

```
sql-quiz/
├── index.html          # 主頁面
├── app.js              # 練習邏輯
├── style.css           # 樣式
├── questions.json      # 題目資料
├── assets/images/      # 題目附圖
└── scripts/
    └── build_questions.py
```
