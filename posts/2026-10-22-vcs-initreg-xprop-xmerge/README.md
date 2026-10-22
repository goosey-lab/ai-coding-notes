# VCS：initreg 与 xmerge 参数速查

- **日期**：2026-10-22
- **标签**：VCS · initreg · Xprop · RTL 仿真

依据：Synopsys《VCS User Guide V-2023.12》；其他版本应核对随安装提供的手册。本文为用法总结，命令未在 VCS 环境实跑。

## 1. 参数放在哪个阶段

| 功能 | 编译/展开：`vcs` | 仿真：`./simv` |
| --- | --- | --- |
| 设置启动初值 | `+vcs+initreg+random` 启用 | `+vcs+initreg+0/1/random/种子` 选值 |
| 使用 xmerge | `-xprop=xmerge` 启用并选择模式 | 正常启动，无须重复添加 |

三步流程 `vlogan → vcs → simv` 中，上述编译/展开选项加在 `vcs` 阶段。[1]

## 2. initreg 的基本用法

```bash
# 编译一次，启用初始化能力
vcs -sverilog -f filelist.f +vcs+initreg+random -o simv_init

# 以下运行命令任选一条
./simv_init +vcs+initreg+0
./simv_init +vcs+initreg+1
./simv_init +vcs+initreg+random
./simv_init +vcs+initreg+12345
```

| 运行参数的后缀 | 含义 |
| --- | --- |
| `0` | 各 bit 初值为 0 |
| `1` | 各 bit 初值为 1，如 8 位变量为 `8'hFF` |
| `random` | 各 bit 随机取 0/1，使用默认种子 |
| `12345` | 各 bit 随机取 0/1，使用种子 12345 |

数字 12345 是种子，不是寄存器赋值；0、1 有特殊含义，不能作为这里的随机种子。初始化在零时刻进行，随后由 RTL 正常驱动。只在运行阶段加参数不能替代编译时启用。[1]

按层级限定范围可使用 `+vcs+initreg+config+配置文件`；运行时配置可覆盖编译时配置，但编译时须已启用 initreg 支持。[1]

## 3. xmerge 的基本用法

```bash
vcs -sverilog -f filelist.f -xprop=xmerge -o simv_xmerge
./simv_xmerge
```

`xmerge` 改变 X 的传播规则：控制条件为 X 时，受影响的结果更悲观地传播为 X。`initreg` 设置初值，两者用途不同。只写 `-xprop` 时默认使用 `tmerge`。[1]

## 4. 组合使用的版本限制

V-2023.12 的 Xprop “Limitations” 明确列出不支持与 `+vcs+initreg` 配合。以上两套命令应分别构建、运行；不能默认其他版本支持组合使用。[1]

## 参考资料

[1] Synopsys, *Verification Continuum™ VCS User Guide*, V-2023.12：

- Chapter 4：Initializing Verilog Variables, Registers, and Memories。
- Appendix D：Option for Initializing Verilog Variables, Registers and Memories at Runtime。
- Chapter 12：Using X-Propagation、Specifying X-propagation Merge Mode、Limitations。

[公开镜像全文](https://device.report/m/21147a58a2161729f264107c63437223e00ed7e3bf0dc09504e86cb06b5da352)（文档作者为 Synopsys，镜像站点并非 Synopsys 官方发布站点）。

