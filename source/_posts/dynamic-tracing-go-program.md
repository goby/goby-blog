---
title: Dynamic tracing Go program
date: 2017-08-22 21:22:21
tags: [go, trace, uprobe, "performance tuning"]
---



## About dynamic tracing

Before do any trace with Linux tracing tools, we should read this paper by Jim Keniston, et: 
[Ptrace, Utrace, Uprobes: Lightweight, Dynamic Tracing of User Apps][1].

## What is uprobes

uprobes is a user-space dynamic tracing tool provided in [Linux 3.5][2] and imporved in [Linux 3.14][3].
[Brendan Gregg][5] said it imspired by [Ftrace][4], which can trace any function in kernel.

>   There are currently two types of user-space probes: uprobes and
uretprobes (also called return probes).  A uprobe can be inserted on
any instruction in the application's virtual address space.  A return
probe fires when a specified user function returns.  These two probe
types are discussed in more detail later.

By Jim Keniston introduced in [SystemTap][6]. 

### How does Uprobes work

Here's Uprobes doing[[link][6]]:

- user provide a binary/library and a virtual address of target function(typically the offset instead of va)
- Uprobes makes a copy of the probed instruction, pause the probed application, if running
- Replace the first byte(s) of the probed instruction with breakpoint instrument(eg, int3 on x86_64)
    - The same machinism of ptrace, copy-on-write, so only affects on target process
    - Even the shared library
- Resume the paused application
- When CPU hit breakpoint instrument, a trap occurs, save CPU user-mode register, and generate a SIGTRAP
- Uprobes accepts the SIGTRAP signal and find out associate probe
- Executes the associated handler, if existed, and passes the probe struct and the saved register.
- REMARK: handler may block, and **the probed thread is stopped when handler running**
- Next, Uprobes single-steps its copy of the probed instruction and
resumes execution of the probed process at the instruction following
the probepoint

### How does Uretprobes work

- Same with previous section's step 1
- Uprobes setup a probe at the entry to the function
- When funtion called, the probe hit, Uprobes save the return address
- Replace the return address with a `trampline` address -- a piece of code that contains a breakpoint instruction
- When the probed function returned, the return instruction is executed, enter the `trampline` area
- Uprobes calls user-define handler
- Sets the saved instruction pointer to the saved return
address, and that's where execution resumes upon return from the trap.

Infact, tracing multi-thread application is hard, and in Go environment. The Go scheduler will
weave instruction on-the-fly, and change `%sp` and `%pc` on demand.

## How to use Uprobes

The document in kernel doc, [Uprobe-tracer: Uprobe-based Event Tracing][7], introduced the usage of
latest uprobes. 

Before start, we must make sure the kernel support Uprobes, please checking:
- `CONFIG_UPROBE_EVENT=y` in `/boot/config-$(uname -r)`
    - deps on kernel version, you can simply grep `UPROBE` and ensure all config is set to `y`
- `/sys/kernel/debug/` directory is existing (maybe `mount -s debugfs`)

The probes stored in `/sys/kernel/debug/tracing/uprobe_events` and
the details in `/sys/kernel/debug/tracing/events/uprobes/<EVENT>`.

### Synopsis 

Create a probe by `echo <probe> > /sys/kernel/debug/tracing/uprobe_events`. And here's the
`<probe>` synopsis:

```
==>
  p[:[GRP/]EVENT] PATH:OFFSET [FETCHARGS] : Set a uprobe
  r[:[GRP/]EVENT] PATH:OFFSET [FETCHARGS] : Set a return uprobe (uretprobe)
  -:[GRP/]EVENT                           : Clear uprobe or uretprobe event

  GRP           : Group name. If omitted, "uprobes" is the default value.
  EVENT         : Event name. If omitted, the event name is generated based
                  on PATH+OFFSET.
  PATH          : Path to an executable or a library.
  OFFSET        : Offset where the probe is inserted.

  FETCHARGS     : Arguments. Each probe can have up to 128 args.
   %REG         : Fetch register REG
   @ADDR    : Fetch memory at ADDR (ADDR should be in userspace)
   @+OFFSET : Fetch memory at OFFSET (OFFSET from same file as PATH)
   $stackN  : Fetch Nth entry of stack (N >= 0)
   $stack   : Fetch stack address.
   $retval  : Fetch return value.(*)
   $comm    : Fetch current task comm.
   +|-offs(FETCHARG) : Fetch memory at FETCHARG +|- offs address.(**)
   NAME=FETCHARG     : Set NAME as the argument name of FETCHARG.
   FETCHARG:TYPE     : Set TYPE as the type of FETCHARG. Currently, basic types
               (u8/u16/u32/u64/s8/s16/s32/s64), hexadecimal types
               (x8/x16/x32/x64), "string" and bitfield are supported.

  (*) only for return probe.
  (**) this is useful for fetching a field of data structures.
```

As forward description, we can setup a uprobe or a uretprobe by a prefix with `p` or `r`.
For example, create a probe in offset `0x2794c0` of application `/home/goby/k8s-bin/kube-controller-manager`
with two arguments, `%sp` for stack pointer and `%ax`:

```
echo "p:p_syncDeployment /home/goby/k8s-bin/kube-controller-manager:0x2794c0 %sp %ax" >> /sys/kernel/debug/tracing/uprobe_events
```

The same to uretprobes.

All of these are well-understood, but what is offset?

### How to get function offset

Function offset is relative to `.text` section, we can get it by following formula:

```
offset(fn) = virtual_address(fn) - virtual_address(.text) + offset(.text)
```

So we need get virtual address of target function and `.text` section. 
We can dump the section headers to get some of them. By `readelf`:

```
$ readelf -S <binary>

There are 46 section headers, starting at offset 0x494fc58:

Section Headers:
  [Nr] Name              Type             Address           Offset
       Size              EntSize          Flags  Link  Info  Align
  [ 0]                   NULL             0000000000000000  00000000
       0000000000000000  0000000000000000           0     0     0
  ...
  [13] .text             PROGBITS         0000000000401a50  00001a50
       0000000001315c54  0000000000000000  AX       0     0     16
```

So:

```
virtual_address(.text) = 0x0000000000401a50
offset(.text) = 0x00001a50
```

Or we can simply get the start address if target application is running:

```
$ grep kube-controller-manager /proc/`pidof kube-controller-manager`/maps |grep r-xp
00400000-02b21000 r-xp 00000000 fe:20 529115  /home/goby/k8s-bin/kube-controller-manager
   |
   \- this is the start address = virtual_address(.text) - offset(.text)
```

Finally, dump symbol table by `objdump`:

```
$ objdump -t <binary> |grep syncDeployment

0000000001e92570 l     O .rodata        0000000000000008              k8s.io/kubernetes/pkg/controller/deployment.(*DeploymentController).syncDeployment.func1.f
00000000006794c0 l     F .text  0000000000000a7f              k8s.io/kubernetes/pkg/controller/deployment.(*DeploymentController).syncDeployment
000000000067b5b0 l     F .text  000000000000016c              k8s.io/kubernetes/pkg/controller/deployment.(*DeploymentController).syncDeploymentStatus
0000000000682b20 l     F .text  0000000000000063              k8s.io/kubernetes/pkg/controller/deployment.(*DeploymentController).(k8s.io/kubernetes/pkg/controller/deployment.syncDeployment)-fm
0000000000682e00 l     F .text  000000000000018d              k8s.io/kubernetes/pkg/controller/deployment.(*DeploymentController).syncDeployment.func1

```

OK, pick what we need, `00000000006794c0` is the va of function. So the offset of function is `0x00000000006794c0 - 0x0000000000401a50 + 00001a50 = 0x2794c0`.

And we can get other functions by these steps.

### Setup uprobe

By following command, we setup a probe to function `k8s.io/kubernetes/pkg/controller/deployment.(*DeploymentController).syncDeployment`:

```
# echo "p:p_syncDeployment /home/goby/k8s-bin/kube-controller-manager:0x2794c0" >> /sys/kernel/debug/tracing/uprobe_events
```

We can check the debugfs, which auto-generated once the probe setupped:

```
root@debian7:/sys/kernel/debug/tracing# tree events/uprobes/
events/uprobes/
├── enable
├── filter
└── p_syncDeployment
    ├── enable
    ├── filter
    ├── format
    ├── id
    └── trigger
```

OK, everything is ok, let's fly:

```
echo 1 > /sys/kernel/debug/tracing/events/uprobes/enable
```

### Trace Result

Once the application call target function. We can get result from `/sys/kernel/debug/tracing/trace`

```
cat /sys/kernel/debug/tracing/trace

# tracer: nop
#
# entries-in-buffer/entries-written: 398/398   #P:4
#
#                              _-----=> irqs-off
#                             / _----=> need-resched
#                            | / _---=> hardirq/softirq
#                            || / _--=> preempt-depth
#                            ||| /     delay
#           TASK-PID   CPU#  ||||    TIMESTAMP  FUNCTION
#              | |       |   ||||       |         |
 kube-controller-26269 [000] d... 8212014.640986: p_syncDeployment: (0x6794c0) arg1=0xc421101d48 arg2=0xd
 kube-controller-26266 [003] d... 8212014.641009: p_syncDeployment: (0x6794c0) arg1=0xc420cf7d48 arg2=0x11
 kube-controller-26267 [002] d... 8212014.641105: p_syncDeployment: (0x6794c0) arg1=0xc4212a1d48 arg2=0x11
 kube-controller-26268 [001] d... 8212014.641547: p_syncDeployment: (0x6794c0) arg1=0xc421239d48 arg2=0xf
```

This result shows who called the function, which cpu run, when called, and the argument we requested.
We can parse this file by a script to get function called frequency, get function latency with a return
probe.

### Further doing

These procedures are too complicated to do. To trace one function maybe ok, but 10? 100? Yes, we can choose
some newer tools if the kernel is newer enough. [bcc](https://github.com/iovisor/bcc) is a nice tool to do
such dirty things.

For example,

```
root@debian7:/usr/share/bcc/tools# ./funccount -p `pidof kube-controller-manager` "/home/goby/k8s-bin/kube-controller-manager:*syncD*"
Tracing 7 functions for "/home/goby/k8s-bin/kube-controller-manager:*syncD*"... Hit Ctrl-C to end.
^C
FUNC                                    COUNT
k8s.io/kubernetes/pkg/controller/deployment.(*DeploymentController).syncDeployment        6
k8s.io/kubernetes/pkg/controller/deployment.(*DeploymentController).syncDeploymentStatus        6
k8s.io/kubernetes/pkg/controller/deployment.(*DeploymentController).(k8s.io/kubernetes/pkg/controller/deployment.syncDeployment)-fm        6
k8s.io/kubernetes/pkg/controller/deployment.(*DeploymentController).syncDeployment.func1        6
Detaching...
```

And the bcc created probes for us:
```
root@debian7:/sys/kernel/debug/tracing# cat uprobe_events
p:uprobes/p__home_goby_k8s_bin_kube_controller_manager_0x2729b0_bcc_30466 /home/goby/k8s-bin/kube-controller-manager:0x00000000002729b0
p:uprobes/p__home_goby_k8s_bin_kube_controller_manager_0x2729b0_bcc_30551 /home/goby/k8s-bin/kube-controller-manager:0x00000000002729b0
p:uprobes/p__home_goby_k8s_bin_kube_controller_manager_0x274be0_bcc_30551 /home/goby/k8s-bin/kube-controller-manager:0x0000000000274be0
p:uprobes/p__home_goby_k8s_bin_kube_controller_manager_0x275430_bcc_30551 /home/goby/k8s-bin/kube-controller-manager:0x0000000000275430
p:uprobes/p__home_goby_k8s_bin_kube_controller_manager_0x2794c0_bcc_30551 /home/goby/k8s-bin/kube-controller-manager:0x00000000002794c0
p:uprobes/p__home_goby_k8s_bin_kube_controller_manager_0x27b5b0_bcc_30551 /home/goby/k8s-bin/kube-controller-manager:0x000000000027b5b0
p:uprobes/p__home_goby_k8s_bin_kube_controller_manager_0x282b20_bcc_30551 /home/goby/k8s-bin/kube-controller-manager:0x0000000000282b20
p:uprobes/p__home_goby_k8s_bin_kube_controller_manager_0x282e00_bcc_30551 /home/goby/k8s-bin/kube-controller-manager:0x0000000000282e00
```

## BUG

Uretprobes is not very stable for golang program, if a return probe enabled and restart the
program, it will panic.

```
runtime: unexpected return pc for k8s.io/kubernetes/pkg/controller/deployment.(*DeploymentController).syncDeployment called from 0x7fffffffe000
fatal error: unknown caller pc
```


[1]: http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.511.7870&rep=rep1&type=pdf
[2]: http://kernelnewbies.org/Linux_3.5#head-95fccbb746226f6b9dfa4d1a48801f63e11688de
[3]: http://kernelnewbies.org/Linux_3.14#head-ca18fd90b3cee1181d74251909e0dda6934b5add
[4]: https://lwn.net/Articles/370423/
[5]: http://www.brendangregg.com/blog/2015-06-28/linux-ftrace-uprobe.html
[6]: https://gitlab.com/fche/systemtap/blob/master/runtime/linux/uprobes/uprobes.txt
[7]: https://www.kernel.org/doc/Documentation/trace/uprobetracer.txt
