title: Setup Virtual hexo With SaaS stack
date: 2017-09-24 13:50:25
tags: []
categories: []
---
使用开源软件服务栈搭建可视化博客，换言之，就是尽量用免费的 SaaS 服务，搭建可视化的完全掌控的博客站点。 这个想法有点奇怪对不对？ 如果想要用， WordPress 不就可以吗？

好了，我的想法就是，用 GitHub Page 托管网站。其次，就是能够支持在线编辑。前者很早就实现了，后者是我最近这段时间两台笔记本都坏了无法修复的情况下，用蓝牙键盘 ＋ 锤子手机蛋疼想出来的。

因为蓝牙键盘没有 Esc 键，以及自己手机里搞一套 nodejs 会不会太蛋疼了。所以就有了这个想法。

基本的博客框架，就是 [hexo](https://hexo.io)。我最早用的是 [hyde](https://hyde.github.io)，但 hyde 的更新很慢，而且文档缺失，自己写插件实在蛋疼。后来发现 hexo 最近很流行，重点是，插件很多，想要随时拿，所以就转到 hexo 来了。转得很顺利，因为刚开始不懂，刚转为 hexo 想自己写主题，看了半天的 API 文档，不知所以然，毕竟对前端不熟。然后网上一搜，就找很到很多资料了。

OK，另外一个呢，是编辑器的支持。还好找到 [hexo-editor](https://github.com/tajpure/hexo-editor) 这款开源软件。那思路就很简单了。刚开始我只是想给它加一个 Image Paste and Upload 的功能，这样就可以随时截图随时贴了。写完，突然想起，我又不想在自己的开发机上做这些和私人的东西，于是就想用随便一个 App Engine 来搭建这个 editor 了。然后脑子里第一个想到就是 heroku!!!

所以，大体的思路如下：

- 在 heroku 上创建 nodejs 的 App，并部署 hexo-editor 的代码
- 给 hexo-editor 添加 git 的功能，部署时，自动拉取博客的 hexo 源码
- 在主界面，添加 Push & Pull 的功能，能够将我们创建的 md 文件
push 到 github
- 利用和 travis 相同的想法，用 aes 加密 deployment key，在应用启动的时候加入 ssh-agent，后续拉取和部署代码用这个 key
- 部署到 github 之后，由 travis 拉去更新，进行编译和生成静态代码，再部署到 github 上的 page repo
- 这样就完成了整个过程了

本来写了一大堆的，因为 session 太短了（一个小时，没有保存），过期重新登陆，缓存没了，干。所以索性把 cookie expiration 设置为 几个月。然后页面插一段 js 代码自动 ping 服务器，这样就能安全地写了。
