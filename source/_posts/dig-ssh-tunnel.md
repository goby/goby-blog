---
title: ssh 隧道挖掘艺术
date: 2017-09-19 18:22:04
tags:
---

我们有一台公网的跳板机，但是我们的开发机不能有外网网卡(你看看，一刀切的厉害)。
所以只好用 ssh 隧道大法。

基本架构如下：
```
                                                          VPC
                                 +-------------+          +---------------------------+
   +-------------+               |             |          |  +-----+ +-----+ +-----+  |
   |             |               | Jump Server |          |  |Host | |Host | |Host |  |
   |  Local PC   +-------------> |   (Proxy)   | <--------+  | A   | | B   | | C   |  |
   |             |               |             |          |  +-----+ +-----+ +-----+  |
   +-------------+               +-------------+          +---------------------------+
```

# Connect a host behinds the firewall

首先我的机器是在防火墙后面，没有公网 IP，每次登陆只能使用 VPN。所幸的是防火墙对 Ingress 控制比较严格， egress 比较松。所以我们可以在某次使用 VPN 登陆 Host 之后，通过反向隧道，打开一条隧道，后面我们的通信都通过这个隧道进行。

在 host-a 中执行：
```
goby@host-a $ ssh -p 2048 goby@proxy -fCNR 20480:localhost:2048
```
意思就是，我们在 host-a 中，将本地的 2048(ssh 端口) 映射到远端 proxy 的 20480 端口。现在 proxy 和 host-a 之间就有了一条隧道：
```
                                             VPC
                   +-------------+          +---------------------------+
+-----------+      |             | <--------+  +-----+ +-----+ +-----+  |
|           |      | Jump Server |  Remote  |  |Host | |Host | |Host |  |
|  Local PC +----> |   (Proxy)   |  Forward |  | A   | | B   | | C   |  |
|           |      |             | <--------+  +-----+ +-----+ +-----+  |
+-----------+      +-------------+          +---------------------------+
```

那么我们在 proxy 上就能通过 20480 访问 host-a。
例如：
```
goby@goby-thhinkpad $ ssh -p 2048 goby@proxy ssh -p 20480 goby@localhost
```
如果我们在防火墙后有 N 台机器，都通过这种方式也太恶心了，怎么办？我们只好把 host-a 也当成第二层跳板机，通过前面创建的隧道。

所以，我可以在本地启动 ssh-agent，通过 Forward Agent 将本地 key 带过去。例如：
```
goby@goby-thhinkpad $ ssh -A -p 2048 goby@proxy ssh -A -p 20480 goby@localhost
goby@host-a $ ssh goby@host-k8s
goby@host-k8s $
```

熟练使用 ssh_config 的，完全可以将上面合并掉，在本地直接访问，例如我的 debian wheezy 上的 ssh_config：
```
Host host-a
  Hostname 127.0.0.1
  User goby
  Port 20480
  ForwardAgent yes
  ProxyCommand ssh -q -W %h:%p goby@proxy -p 2048
  # 某些 ssh 版本，例如 mingw64 要用 nc
  # ProxyCommand ssh goby@proxy -p 2048 nc %h %p
```

本地就能透明访问 host-a 了。

# Create a local proxy upon a tunnel

如果仅仅是反向代理，好像也没什么。但是如果，我们开发调试时，需要代理，例如 web 页面，从本地直接访问怎么办？我们就需要将 host-a 当成代理了。
所以这时候就需要在前面创建的隧道之中，再创建一个动态隧道代理：

```
goby@proxy $ ssh -CNfD 17708 goby@localhost -p20480
```

那么在跳板机上就会开启 17708 端口，用于动态隧道。最后我们要把跳板机上的 17708 端口映射到我们本地 PC 上，登陆时候使用 L 参数即可：
```
goby@goby-thinkpad $ ssh -A -p 2048 goby@proxy -L 7708:localhost:17708
```

那么我们就可以在本地使用 Chrome， 配置代理 SOCK4: localhost 7708 访问 host-k8s 的 IP。（搭配 Proxy SwitchOmega 使用风味更佳）

# Mapping local port to remote

在这个艰难的环境里，我们还可以做得更多，在这个 Fucking GFW 的局域网，我们开发中经常要用到代理。那么我们的简单想法，就是将本地代理端口映射给开发机。
例如本地端口是 8808，想在 host-a 上开一个公共代理12307给其他所有的node用，那么我们个前面的那个ssh_config 添加 RemoteForward 就可以了

```
Host host-a
  Hostname 127.0.0.1
  User goby
  Port 20480
  ForwardAgent yes
  RemoteForward 12307 localhost:8808
  ProxyCommand ssh -q -W %h:%p goby@proxy -p 2048
  # 某些 ssh 版本，例如 mingw64 要用 nc
  # ProxyCommand ssh goby@proxy -p 2048 nc %h %p
```

当然，记得给 host-a 上的 sshd 配置 `GatewayPorts yes`，否则默认 12307 就监听在 loop 上。
