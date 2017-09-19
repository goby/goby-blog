---
title: SynProxy 工作原理
keywords: 
uuid: fc0b7eee-1ccc-4d39-83ac-0f62a64e7ba1
date: 2015-12-17 01:37:44
tags:
 - tech
---

[TOC]

## SynFlood 简述

Syn Flood 从1994年就被发现到现在，一直以来都是较为简单、有效的DDoS攻击手段。虽然如今很多在实现TCP/IP协议栈的时候采用了很多方法来减缓Syn Flood的攻击（比如[Syn Cookie][syncookies]、 [TCP Cookie Transaction][tcpct]），但是今天的DDoS攻击中Syn Flood的占比依旧[高达58%][yundi]。最近两三年随着各种公有云的兴起，DDoS攻击流量也从原来的几十Gps上升到400Gps，所以威胁并没有随着网络性能提升而得到减缓。比较系统的介绍SynFlood攻击和防御可参见([TCP SYN Flooding Attacks and Common Mitigations][rfc4987])。当前防护Syn Flood的手段主要有三种：


 1. 丢包模式，利用TCP重传机制，丢弃首个 Syn 包。
    当系统收到Syn包时，进行计数，如果该SYN包的来源IP是首次到达，那么就丢弃处理。
    这种防御方法也是最简单、比较有效的方式，能够防御所有的伪造源IP的Syn Flood攻击。
    但是根据RFC793以及各种实现来看，Syn包的首次重传至少有1秒的间隔，
    非常影响正常用户的体验，以及也没有办法防御来自固定源IP的攻击；
 2. 反向探测，即向Client发送探测包。
    就是当收到Syn包时，系统先向Client发送可用来验证合法请求的数据包，
    比如常见的是返回响应码不正确SynAck包，然后再根据Client返回的Reset包来判断该Client的合法性。
    这种方法不仅能够防御伪造源IP，也能防御固定IP的攻击。
    但是有个缺点是当Client有比较高级的防火墙会丢弃非法的SynAck包时，会造成误杀；
 3. 代理模式，即Syn Proxy，把DDoS设备当成代理。
    这种模式类似于目前负载均衡设备的功能，防御设备先伪造Server与Client建立连接，
    然后再与Server建立连接，双向连接建立好之后再进行数据转发。
    显然这种方式能够拦截所有想要发起Syn Flood 的 Client，
    甚至如果做得复杂些也能防御应用层的大部分攻击（比如CC、 [Slowloris][]）。
    但是这种模式也比较复杂，如果实现不好反而容易被攻击。
    而且这种模式对于网络架构上也有比较高的要求，Client-Server双向均需要经过
    （前两种模式只需要部署在Client--> Server单向中，如果你比较熟悉LVS的话，
    丢包模式和反向探测都可以工作在DR或者TUN模式下，而代理模式只能工作在NAT/FullNAT模式下）。
    这种防御手段一般是实现成另外一种比较容易的方式：
    如果与Client建立连接之后就立即断开连接，并认为Client可信，
    但这种方式的缺点是会影响用户体验，需要Client再次发起连接。

下文将简要介绍下Syn Proxy的设计和实现（下文简称为 Proxy）。
Syn Proxy 早在6、7年前已经有人在内核的netfilter框架中[实现][synproxy]了，
后来百度、[阿里][lvs]、360等的LVS也有实现，本文也参考了他们的设计。

## SynProxy一般流程
Syn Proxy的主要流程是与Client三路握手、与Server三路握手、转发数据。
因此大致的数据流如下图：

![three way hands shake](/assets/img/synproxy/flow.png)

上述流程分为四个阶段：

 - T1: Client 与 Proxy 三路握手
 - T2: Proxy 与 Server 三路握手
 - T3：Client与Server之间传输数据
 - T4: Proxy 清理资源
    
四个阶段的状态变迁如下图：

![stat transfer](/assets/img/synproxy/stat.png)

###优点：

 - 只有在 Client 与 Proxy 三路握手之后才会与 Server 连接，实现了对Syn Flood的防御
 - 利用 Syn Cookie 原理，实现对非 Syn 包有 Cookie 检测，不符合Cookie算法数据包直接丢弃，可以实现对TCP标志位攻击的防御
   
###挑战：

 - T1阶段 WinSize 处理
 - T1阶段其他扩展，比如TFO(TCP Fast Open)、带payload
 - T1阶段 TCP Options 的处理，包括MSS、WinScale、Timestamp等，发起前并未知 Server 配置
 - T1之后，T2还没完成之前，Client push数据会被丢弃
 - T2阶段的处理，目标是否可达、目标的端口是否开启
 - T2阶段记录Proxy生成的SeqNumber与Server生成的SeqNumber之间的差别，用于T3转发的矫正
 - T3阶段对 SeqNumber 的矫正
 - T4阶段的资源回收

接下来先介绍下 Syn Cookie 的算法。
        
## Syn Cookie 生成和验证
Syn Cookie生成不同操作系统的实现，最原始算法见[SYN cookies]，一般都由若干密钥、时间、MSS以及四元组决定。在linux kernel 2.6.32 中是下面这个公式：

    syn_cookie = hash1 + syn_seq + current_time * 2^24 + hash2 + MSS % 2^24

其中：

    hash1 := hash(sec1, saddr, daddr, sport, dport)
    hash2 := hash(sec2, saddr, daddr, sport, dport, current_time)
    syn_seq : client发起的sequence number
    current_time: 收到SYN包的时间，以分钟位单位
    sec1, sec2 := 加密种子

当进行校验时，首先校对时间，从上式发现，时间与为syn_cookie的高8位决定，高八位由时间、hash1和syn_seq决定：

    time = (syn_cookie - hash1 - syn_seq)/(2^24)

如果time合法（内核以分钟为单位），则可以确定hash2，因此MSS也可以确定，再对MSS进行判定。

## T1阶段处理

T1阶段Proxy并不知道后端的情况，包括WinSize大小、MSS大小、WinScale及Tcpstamp开启情况、扩展支持情况(比如TCP Fast Open)

### WinSize处理

WinSize的处理比较简单，有两种解决方案，一种取 Linux 默认大小4096，另外一种取0。当WinSize取0时，根据TCP协议，Client是不应该PUSH数据过来的，这时我们可以等T2阶段Server响应Proxy的SynAck，从中取得WinSize再通过Ack包发送给Client，同时这样也可以避免在T2握手完成之前Client Push数据过来。

### TCP Options处理(MSS、SACK、Tcpstamp、WinScale)

这几个参数的处理比较难办，MSS、SACK、WinScale只能在SYN包中出现，因此在选择时就需要进行评估，好在 Server 是我们自己管理的，因此这三个选项可放在配置中。但是Timestamp的处理就比较麻烦。Timstamp使得接收方能够在收到Ack之后计算RTT，在这个解决方案中我们并不能保证T1阶段Proxy给Client的timestamp 不比 T2阶段Server给Proxy的Timestamp大。因此如果需要启用Timestamp的话需要保存与T2阶段获取的Server段的Timestamp的差值 DeltaTimestamp。

### SYN Cookie 算法的改进

从上一节我们发现Syn Cookie中，高8位可以还原Time和MSS，那么还有低24位是不是可以用来放置 SACK、Timestamp和WinScale呢？阿里开源的LVS中就用下面的[算法][cookie_algo] 来改进Syn Cookie:

![code of syn cookie](/assets/img/synproxy/code.png)

### T1阶段防御

收到Client的Syn包，计算Syn Cookie，配置WinSize=0以及TCP Options，响应SynAck。对 Client 发过来的Ack包进行解析，判定是否合法。这个阶段可以丢弃同一链路上所有的push包。需要注意的是这个阶段需要Client发过来的Sequence Number、MSS、WinScale，其中Sequence Number可以通过最后的握手包直接获取而无须额外保存，但Client的MSS可能小于我们Server之间协定的MSS。

## T2阶段
T2阶段发生在Client全连接建立之后，当收到Client的Ack包时，我们认定该Client是合法Client（非Syn Flood 攻击源），那么我们就可以向后端发起三次握手，握手信息从T1阶段最后的Ack包中复原Client的Sequence Number， 从Ack包的 AckNumber 复原 SACK、WinScale、MSS等信息拼接 TCP Options，向Server发送Syn包。

当接收到Server的SynAck包时，除了给后端发送Ack完成三次握手，还需要获取其中的WinSize和Sequence Number，将WinSize值以Ack包发给Client告诉Client可以发送数据了（Ack包的信息，Sequence Number来源T1阶段的保存，Ack Number可以从SynAck包复原，WinSize值从SynAck包复原）。

这个阶段需要记录Proxy 生成的Sequence Number和 Sever生成的 Sequence Number 之间的差值 DeltaSeq。

这个时候后端Server有三种可能的状态，一个是主机不在线，第二个是主机在线但繁忙，第三是主机可达但是端口没开。前两种情况的表现比较一致，需要Proxy有重传机制。如果主机不在线，这个时候，Client可能会发送Window Probe过来，这时proxy也需要回复ZeroWindow（亦可丢弃，因为client会重传）。第三种情况主机返回RST，此时Proxy需要给Client发送RST并进入T4阶段。如果这个阶段刚好收到Client的 RST 或者 FIN 包时，则给后端发送RST并进入T4阶段。

### T2阶段防御

T2阶段能够防御所有Client的TCP标志位攻击，因为这个时间段所有的Client过来的数据包（除了FIN和RST）均会被人不过T2阶段一般时间很短。
    
## T3&T4阶段
T3阶段是数据转发阶段，需要利用T2阶段获取的DeltaSeq对双向数据包进行 Sequence Number 和 Acknowledge Number进行修正。如果收到任何一方的Reset或者FinAck包时，需要进行转发并进入T4阶段。在断开连接有四次挥手的状态变化，但这里简化处理并没有加以判断。

T4阶段一般来说比较短暂，主要是重置标志位、移除Hash key等。

### T3&T4阶段防御

这个阶段需要注意防止慢攻击、小包攻击，因此需要加入超时机制（测速）以及小包检测。在计时器溢出或者检测频繁小包的时候给Server和Client发送 RST 并进入T4阶段。


## LVS中的实现

目前 SynProxy 模式被广泛应用于LVS中，如前文提到的阿里、小米、UC等的开源版本。其思路主要是：

* 在NF_INET_PRE_ROUTING处 ip_vs_pre_routing hook函数中获取Client的Syn包，获取syn包、并回复SynAck
* 同在NF_INET_PRE_ROUTING处的 ip_vs_in --> tcp_conn_schedule 中处理与Client三路握手的Ack包，校验cookie成功后创建ipvs的session信息，完成T1阶段，并构建Syn包发送给RealServer，同时注册timer用来处理重传，进入T2阶段
* 在NF_INET_FORWARD的ip_vs_out中处理RealServer返回的SynAck，记录 DeltaSeq、DeltaTimestamp，向Client发送包含RealServer WinSize 的Ack包、向RealServer发送三路握手的Ack包，进入T3阶段
* 在tcp_dnat_handler/tcp_fnat_in_handler中修正AckSeq以及SACK中的AckSeq、Timestamp
* 同样，也在tcp_snat_handler/tcp_fnat_out_handler中修正


[rfc4987]: https://tools.ietf.org/html/rfc4987 "TCP SYN Flooding Attacks and Common Mitigations"
[tcpct]: https://tools.ietf.org/html/rfc6013 "TCP Cookie Transaction"
[syncookies]: http://cr.yp.to/syncookies.html "Syn Cookie"
[yundi]: http://www.thegitc.com/phone/pptDown/2015/ppt/%E5%88%86%E4%BC%9A%E5%9C%BA/306%E5%AE%89%E5%85%A8/11%E6%9C%8819%E6%97%A5/1%E5%88%98%E7%B4%AB%E5%8D%83%E2%80%94%E7%94%B5%E4%BF%A1/%E5%88%98%E7%B4%AB%E5%8D%83%E2%80%94DDoS%E7%9A%84%E7%8E%B0%E7%8A%B6%E3%80%81%E8%B6%8B%E5%8A%BF%E5%92%8C%E5%BA%94%E5%AF%B9.pdf "云堤报告"
[cookie_algo]: https://github.com/alibaba/LVS/blob/master/kernel/net/ipv4/syncookies.c#L381
[lvs]: https://github.com/alibaba/LVS
[synproxy]: https://github.com/xiaosuo/xiaosuo/tree/master/synproxy
[Slowloris]: https://en.wikipedia.org/wiki/Slowloris_(software)

{# Local Variables:      #}
{# mode: markdown        #}
{# indent-tabs-mode: nil #}
{# End:                  #}

