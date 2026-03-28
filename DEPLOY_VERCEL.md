# Vercel 部署指南

## 第一步：安装 Vercel CLI

```bash
npm install -g vercel
```

## 第二步：登录 Vercel

```bash
vercel login
```

浏览器会打开，用你的 GitHub/Google 账号登录（都免费）

## 第三步：部署

在项目目录下运行：

```bash
cd "/Users/apple/Desktop/Claude/IO Crawler"
vercel
```

按照提示：
- **Project name?** → 按 Enter（默认：`io-crawler`）
- **Which scope?** → 选你的用户名
- **Link to existing project?** → 选 `N`（新项目）
- **Directory?** → 按 Enter（默认：`.`）

## 第四步：完成！

部署完毕后，你会看到：
```
✓ Production: https://your-app.vercel.app
```

**现在你可以直接访问这个 URL，在公网上使用爬虫了！**

---

## 常见问题

### 1. 爬虫超时怎么办？
Vercel 免费版的函数超时是 10 秒，但爬虫需要更长时间。

**解决方案：** 升级到 Pro（$20/月）或使用后台任务：
- Vercel Cron 功能（需要 Pro）
- 或者改用 Railway/PythonAnywhere

### 2. 数据库会丢失吗？
是的。Vercel 是无状态的，每次部署容器都会重置。

**解决方案：**
- 连接到外部数据库（MongoDB Atlas 免费层）
- 或改用 Railway（支持持久化存储）

### 3. 想要更多功能？
推荐改用 **Railway**，它更适合 Python 全栈应用：
```bash
railway link
railway deploy
```

---

## 本地测试

部署前可以本地测试：
```bash
vercel dev
```

这会在 http://localhost:3000 启动开发环境。
