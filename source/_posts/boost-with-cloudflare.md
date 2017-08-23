---
title: Boost Your Blog with CloudFlare
keywords: 
date: 2016-12-26 18:45:10
uuid: f95667b5-57f8-4c6f-b839-3fe53a0eb668
tags:
 - tech
---

# 为什么要加速

因为众所周知的原因， 在大天朝访问 *.github.io 的速度总是不那么理想， 尤其是
在庆丰朝的今天。 另外因为 Github 最近的[财报不太好][not-cheap]， 为了开源节流，已经把
 [Github Pages 进行限流][pages-limit]了。

我的这个站点很早以前已经经过 CloudFlare 加速了，而且加速效果非常不错。 同时这个站点里头
也用到了 google 的一些服务( Google Fonts 以及 Google 自定义搜索等)，通过 CloudFlare 
也能够实现内容的加速。

# 能够加速的地方

依赖 Cloudflare 的节点, 能够实现 CDN 的加速功能( 但好像看起来我的并不行，
总是被调度到他们的总部，不过这样能够防治某墙对 *.github.io 的干扰， 总体效果依然比
采用了 Fastly CDN 的 github.io 强)。 

# 如何加速

加速基本模型如下：

```
Client <-----> CloudFlare <--> Github Pages Server
```

好在 Github Pages 支持域名绑定，我们把域名给 CloudFlare 解析，然后 CNAME 到 
goby.github.io 即可，记得在配置的时候打开 CDN and HTTPProxy 开关。

然后在 CloudFlare 配置即可。以下介绍下一些关键点。

## HTTP2

打开 CloudFlare 的 Cryto/SSL， 调整成 Flexible 即可。

CloudFlare 如何实现的呢？ 简单地说，就是替我们申请 X.509 证书，帮我们做 SSL 卸载。
然后通过 SAN([Subject Alternative Name][san]) 将一张证书给一堆域名用。比如，我
的证书的 SAN 字段就是这样的：

```
DNS Name=sni152148.cloudflaressl.com
DNS Name=*.atom-design.com.pl
...
DNS Name=*.gobyoung.com
...
```

生成一个带有 SAN 的证书可以参见 [How to setup your own CA with OpenSSL][how-setup-ca]。
从返回的头部也初步判断 CloudFlare 用户前端 Server 就是 Nginx( ningx 大牛章亦春之前就在
它家)， 而 nginx 干这种事情最得心应手。

现在用 Nginx + OpenSSL 做 SSL offload 可以借助硬件，比如 Intel 的 [AES-NI][aes-ni]
加速。

猜想它的后台应该是这样实现：

+ 用户添加一条记录，启用 CDN 以及 SSL
+ 把用户请求分配到某个证书请求队列中，每个队列有一定的编号，比如 sni152148
+ 在比较短的时间内，比如可能是一小时或者十分钟，将所有该队列中的域名放入 SAN 并向证书服务商
发送证书申请
+ 完成，并将获得的证书下发到代理服务器上
+ 在后面某段时间，进行证书之间的 rebalance(即将某个域名转到不同的队列中去, 因为我的网站
的证书变过几次)

因为证书价格不菲，而Let's Encrypt 之类的需要自己去renew，所以直接交给 CloudFlare 帮我们
处理，并且它也支持自动renew。

[not-cheap]: https://www.bloomberg.com/news/articles/2016-12-15/github-is-building-a-coder-s-paradise-it-s-not-coming-cheap
[pages-limit]: https://help.github.com/articles/what-is-github-pages/#usage-limits
[san]: https://en.wikipedia.org/wiki/Subject_Alternative_Name
[how-setup-ca]: https://gist.github.com/Soarez/9688998
[aes-ni]: https://software.intel.com/en-us/articles/intel-advanced-encryption-standard-instructions-aes-ni

## 代理优化

另外一个很强大的功能就是代理优化，比如：

+ Rocket Loader -- 自动优化Javascript，合并 js 文件，并保证第三方的js不会拖慢页面加载速度，
我觉得比较强大的一点，它能够让我直接使用 Google Custom Search
+ Local Storage Caching -- 利用本地缓存(例如 chrome 的 localStorage )，将文件内容写到本地
缓存中，防治网络的重复请求(相对于 HTTP 的 Caching 来说，连网络请求都不用了)，也就是说能直接利用
本地缓存渲染。
+ Cache Header Optimization -- 直接优化 HTTP 头的缓存相关(Date/Expire/Last-Modified 之类的)
+ HTTP2 -- 就如第一节将的，升级成 HTTP2，多路复用、头压缩、请求流优先级等。
+ Server Push -- 这个也是 HTTP2 的一个优势，解读 HTML 内容，在 Client 获取文件之前，一次性
将所需的文件推送给 Client。 常见的比如，当Client 请求 HTML 时，服务端将所需的 CSS、图片等
直接推给 Client， 减少多个 RTT。
+ AutoMinify -- 自动优化 HTML, CSS, Javascript 文件，例如我使用了 bootstrap， [经过优化][opt-bootstrap]
的文件相较于[原文件][ori-bootstrap]，大小降低 32%。
+ Automatic Content Caching -- CloudFlare 的边缘服务器会自动缓存各种静态资源文件，而且通过
TTL 来控制(和 Local Storage Caching 配合)。而且可以配置 TTL，即边缘节点多久回源刷新缓存。

以下介绍下我对这几个功能的理解，以及让我来做，我改怎么实现。

[opt-bootstrap]: https://blog.gobyoung.com/media/js/bootstrap.js
[ori-bootstrap]: https://raw.githubusercontent.com/goby/goby.github.io/master/media/js/bootstrap.js

# 如何实现加速(我认为)

本章介绍下我认为的该如何实现加速。

## Rocket Loader

官方的介绍 [How CloudFlare Rocket Loader Redefines the Modern CDN][how-rocket-loader] 有点陈旧了，
是 2011 年的内容，里头介绍了几点 Rocket Loader 的特点：

+ 保证所有外部包含的 js 均不会阻碍页面加载
+ 所有的js，包含第三方的，都是异步加载
+ 使用单个请求加载所有的 js
+ 使用 LocalStorage 来缓存 js，除非有必须，否则连请求都不用

通过我自己的观察，我发现当前(cloudflarejs-rocketloader-0.11.5 Tue Oct 07 2014 03:19:25)，它实现
方式如下：

+ 首先扫描页面，将所有的 scrypt 的 type 改成 `text/rocketscript`，并将外联的形式的脚本的 `src`
属性改成 `data-rocketsrc`
+ 在页面最开头，注入 `CloudFlareJS-0.1.34`，实际上就是装着所有 CF 在客户端的加速处理脚本(包含一些特殊的高级
功能，比如网站公告等)，由 CloudFlareJS 动态加载 `rocket loader`
+ Rocket Loader 处理所有的 `text/rocketscript` 类型的 `script`，记录嵌入式脚本和外联脚本的
先后顺序，保证原始页面脚本之间的依赖关系
+ 在 Loader 载入完成之后，将所有外联式脚本的地址拼凑起来，发送到 `/cdn-cgi/pe/bag2` 下，其中结果用 `multipart` 返回回来，
比如当前(2016-12-25)观察到的如下:
```http
GET /cdn-cgi/pe/bag2
QueryString 
    r[]:https://blog.gobyoung.com/media/js/modernizr.js
    r[]:https://blog.gobyoung.com/media/js/jquery.js
    ...

RESP
  Content-Type multipart/mixed

  X-Cf-Url: https://blog.gobyoung.com/media/js/modernizr.js
  X-Cf-Status: 200
  ...
```
+ 解析响应结果，将脚本，将结果保存在 LocalStorage 中，如果可用的话，这样，下次请求的时候就会先查询一下
Local Storage，直接去掉无畏的请求
+ 按照页面的顺序执行 js 文件和 js 脚本
+ 我发现我用的 jQuery 的 ajax 自己加载 js 脚本，它也能正确地拦截并进行代理，这用的是什么原理？

有意思的是爆栈上也有类似的[讨论](http://webmasters.stackexchange.com/questions/60276/how-does-cloudflares-rocket-loader-actually-work-and-how-can-a-developer-ensur)
，和我的看法大同小异。

这个虽然看起来比较简单，但是实现起来可能有一堆细节要处理（各种浏览器的兼容性、框架兼容性等），
比如我使用的是 Google Custom Search，每次搜索都是拼凑 URL， 结果它也都给我缓存起来了，实质上这些
请求都是暂时的，这也是它的 bug 之一吧。

我来实现的话，认为需要实现以下几个部分：

1). 实现聚合的 Nginx 模块可以利用 subrequest + upstream 简单实现请求的聚合，如下
```
              / subrequest 1.js -- upstream
MainRequest -+- subrequest 2.js -- upstream
              \ subrequest 3.js -- upstream
```
在实现的时候需要在 main request 把所有的 subrequest 的关键 header 拿到，
写入响应 body 中。 在实现中，只需要提取与缓存相关的头即可，第二个是要防止恶意攻击，
比如递归请求。第三个本地缓存的重要性。

2). 实现改写 HTML 的 Nginx 模块，这个直接使用现有的模块 [ngx_http_sub_module][sub-module]
即可。例如：
```nginx
location / {
  sub_filter '<script>' '<script type="text/rocketscript">';
  sub_filter '<script src=' '<script data-rocketsrc=';
  ...
}
```
另外一个就需要在 `<head>` 标签的里头插入 Rocket Loader 的引用，例如：
```html
<script>
  try {
    document.write('<script type="text/javascript" src=//...></script>');
  } catch(e) {}
</script>
```
用 [nginx_http_substitutions_module][subs-module] 直接用 正则表达式，能实现
更加强大的功能， 不过还需要和上面的需求一样，需要一个缓存保障性能。(其实不能简单地进行正则
替换，需要对整个 DOM 树进行解析，否则在部分场景下，比如有 `<pre>` 的时候会出问题)

3). 客户端 Rocket Loader 的实现，简单的实现如下:
```javascript
  var scripts = document.getElementsByTagName('script');
  var rockets = [];
  scripts.forEach(function(i, e){
    // 将 rocket 脚本、外联脚本以及不在本地缓存中的脚本加到请求队列中
    if (isRocketScript(e) && isExternalScript(e) && !inLocalStorage(e)) {
      rockets.push(e);
    }
  });

  // 组建请求，并设置回调
  getScripts(rockets, function(resp) {
    // 将返回结果放到缓存中
    for (var p : resp.parts) {
      saveLocalStorage(p);
    }
    // 按顺序执行脚本
    runScripts(scripts);
  });
```

如何解决 rocket loader 的兼容性问题呢？

[sub-module]: http://nginx.org/en/docs/http/ngx_http_sub_module.html
[subs-module]: https://github.com/yaoweibin/ngx_http_substitutions_filter_module
[how-rocket-loader]: https://blog.cloudflare.com/56590463/



{# Local Variables:      #}
{# mode: markdown        #}
{# indent-tabs-mode: nil #}
{# End:                  #}
