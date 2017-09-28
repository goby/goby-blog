title: pipe(7) 原理与实现
date: 2017-08-09 09:07:41
tags: []
categories: []
---
title: pipe(7) 原理与实现
date: 2017-08-09 09:07:41
tags:
---

pipe(7) 在我们日常工作中经常碰到，能够串联 Linux & Unix 下各种工具的输入输出，组成一个动态的功能强大的数据处理流，是 Unix 设计哲学的一种体现。最近一次对其进行关注是因为微信群里有人说 pipe 操作会完成 4 次内存拷贝。所以究其原因或者说明对错，就展开一段考究之旅，了解 pipe 发明以前近 50 年的变化（是的，就是这么古老，比 Unix 还古老）和顺便学习 vfs 相应的知识。

## Unix Pipe 起源

### pipeline 想法的萌发

根据[维基百科][1]和 [/sys/doc/][2]的说明，Unix 的 Pipeline 概念最初由 [Doug McIlroy][] 发明。 当时， McIlroy 认为，从一个程序输出到文件，再输入另一个程序非常耗时。互联网总是那么神奇，保存了当时 pipeline 的初衷：

> \- 10 -
>
>  Summary--what's most important.
>
>    To put my strongest concerns into a nutshell:
> 1. We should have some ways of coupling programs like
garden hose--screw in another segment when it becomes when
it becomes necessary to massage data in another way.
This is the way of IO also.
> 2. Our loader should be able to do link-loading and
controlled establishment.
> 3. Our library filing scheme should allow for rather
general indexing, responsibility, generations, data path
switching.
> 4. It should be possible to get private system components
(all routines are system components) for buggering around with.
>
> M. D. McIlroy
>
> October 11, 1964 


![The Origin of Unix Pipes](http://doc.cat-v.org/unix/pipes/pipe.png)

McIlory 认为当时一个最重要的事就是找到一种类似花园浇水软管的方式，组合不同程序的输入输出，就像一条信息流一样。

### Unix Pipe 与 `|` 标记

在 19 年后的 1973 年，当 [Ken Thompson][kt] 在 Research Unix 第三版中引入 `pipe()` 系统调用的时候，MiIlroy 非常兴奋:

> "... in one feverish night ... The next day, saw an unforgettable orgy of one-liners as everybody joined in the excitement of plumbing"

不过当时 pipeline 并不是 Unix 独有的，在 Dartmouth Time-Sharing System 中也有 "communication files" 的概念。

在 [Dennis Ritchie][] (他老人家也在 2011 年 10 月 12 日去世去世，那一周乔布斯也去世了，世界媒体和人们对两者的关注度天差地别，不过这是另外一个话题了，许多年后的今天有时我们还能看到有人试图去比较批判人们对两个人的态度) 老先生的 ["The Evolution of the Unix Time-sharing System"][evolutionofunix] 论文中的描述，McIlroy 的想法是，在程序的前后，表明输入输出，例如 `copy` 指令：

    inputfile copy outputfile

为了更直观表示 pipeline， 不同命令可以组合起来。因此例如 `sort` 一个 `input` 文件，然后由 `paginate` 进行分页，最后用 `print` 打印结果，可以表示为：

    input sort paginate print

对应的如今的表示为：

    sort input | pr | opr

他说，这个想法，在当时某个下午写在黑板上，然而并没有立即行动起来。当时有几个问题亟待解决：

1. 插入文件的符号太过怪异了，因为我们通常用 `cp x y`  表示拷贝 `x` 到 `y`
2. 同时也没办法区分到时是命令参数还是输入文件还是输出文件; 
3. 这种命令执行的 IO 模型看起来不实用

最终，在 McIlroy 的坚持下， `pipe` 最终还是加到系统中，同时用一种新的符号表示， 和 IO 重定向使用同一种符号。例如，上面的那个例子表示为：

    sort input >pr>opr>

类似重定向文件的思想，把 前一个命令的输出重定向到下一个命令上，当成下一个命令的输入。最后的 `>` 在上面的例子是必须的因为最后表示输出到 Console，否则会当成重定向 `opr` 文件中。

当时 pipeline 很快就让大家接受了，同样迸发出类似 `filter` 的词。很多命令都积极适配 pipeline。例如，当时没人能够想象有人要 `sort` `pr` 在没有参数下排序或者打印标准输入。

然后，不久之后各种问题接踵而至。大部分都是愚蠢的语法问题，比如 `>` 命令后的字符串用空格分隔，就像我们给 `pr` 加了参数，我们就必须加双引号：

    sort input >"pr -2">opr>

还有就是，我们尝试让这个标记更佳通用，例如 pipe 接受输入标记 `<`，这意味着标记并不唯一。例如有人会写成：

    oopr <pr<"sort input"<

甚至

    pr <"sort input"< >opr>

就这样，随着第三版的发布，这种表示法持续了几个月，Thompson 提出的`|` 在第四版横空出世。然而，即使 `|` 到如今依然延续着，但是它一个非常明显的缺点就是直愣愣地只能线性传递。例如，如何优雅比较两个命令的输出？如何优雅标记一个命令的两个并行输出？

有意思的是， Ritchie 最后对“unix pipe 是 Multics 文件流拼接的延续” 的看法嗤之以鼻。当然，我并没有对 Multics 文件流拼接进行探讨，那已经是上古时代的东西了。但管道的出现，让命令本身语意用法不变的情况下组合起来形成复杂的程序。

> The mental leap needed to see this possibility and to invent the notation is large indeed.

`|` 这个符号表示管道，由于非常形象生动，这个表示延续至今，并移植到非常多的操作系统中，例如 DOS, OS/2, Microsoft Windows, BeOS 等。甚至， Mac OS(X) 中的 Automator 的图标也是向这个发明致敬。

![automator](https://www.blogcdn.com/www.tuaw.com/media/2012/12/automator.png)

另外在 [communicating sequential processes](https://en.wikipedia.org/wiki/Communicating_sequential_processes) （我想有空，也想谈谈 CSP，特别是最近一年一直都在用 golang ）也受到最初的 McIlroy 的想法的影响。

当然这个思想也形成软件工程中 ["Pipe & Filter Design Pattern"](https://en.wikipedia.org/wiki/Pipeline_(software)).

最后，不得不说一句，令人遗憾的是，根据 [Warren Toomey][] 的说法，他在 1999 年 1 月拿到 Dennis Ritchie 关于 Research Unix V3 的拷贝 ，但却没有完整地留存下来，而遗留下来的版本，如今放在[阿尔卡特朗讯][3]的网站上，却刚好遗失了 `pipe()` 相关的源码，实在令人扼腕（这不得不说起台湾清华大学的开放课程 [《科幻概论》][4] 的授课老师郑运鸿先生的话，大意是“这个科技时代吊诡的是想要保存的总会丢失，不想要的总是存在世界的某个角落”，这里借用下字面意思）

> In partijust got the 'nsys' kernel
to boot, so I have not had a chance to sit down and work out exactly what
functionality is missing.
>
> http://www.tuhs.org/Archive/Distributions/Research/Dennis_v3/

同样， Research Unix V4 在 Dennis Ritchie 贡献出来的非常接近最终 Release Version 的[版本][5](下面的引用也来自这里)也缺少 `pipe`， 他说：

> This is a tar archive derived from a DECtape labelled "nsys". 
What is contains is just the kernel source, written in the pre-K&R dialect of C. 
It is intended only for PDP-11/45, and has setup and memory-handling code that will not work on other models (it's missing things special to the later, smaller models, and the larger physical address space of the still later 11/70.) 
It appears that it is intended to be loaded into memory at physical address 0, and transferred to at location 0.
>

## Linux pipe 的设计实现

好，考古之后，我们直接进入 Linux pipe(7) 的最新实现，总的来说，pipe 实现如下：

- 在 vfs 中有一个 pipefs 模块，在内核启动的时候挂载进去
- pipefs 与其他文件系统不同，并不是挂载根目录 `/` 下，而是专门的根 `pipe:`
- pipefs 无法像普通文件系统那样直接访问
- pipefs 的入口在 `pipe(2)` 系统调用
- `pipe(2)` 在 pipefs 中创建一个文件，然后返回连个 fd，一个用于读一个用于写
- pipefs 是内存文件系统

### Virtual File System

// TODO


[1]: https://en.wikipedia.org/wiki/Pipeline_e System

首先我们从 VPS 讲起， VFS 即 [Virtual File System](https://en.wikipedia.org/wiki/Virtual_file_system)，简单来说，就是一个文件系统的抽象，
定义一定的接口将各种类型的文件系统的接口统一。




[1]: https://en.wikipedia.org/wiki/Pipeline_(Unix)  "Pipelin Origin of Unix Pipes"
[3]: http://www.tuhs.org/Archive/Distributions/Research/Dennis_v3/
[4]: http://ocw.nthu.edu.tw/ocw/index.php?page=course&cid=3 
[5]: http://minnie.tuhs.org/cgi-bin/utree.pl?file=V4
[Doug McIlroy]: http://genius.cat-v.org/doug-mcilroy/
[kt]: https://en.wikipedia.org/wiki/Ken_Thompson
[Dennis Ritchie]: https://en.wikipedia.org/wiki/Dennis_Ritchie
[evolutionofunix]:https://www.bell-labs.com/usr/dmr/www/hist.html
