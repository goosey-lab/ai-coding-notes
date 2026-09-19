# VCS 波形分割实测：按任务完成节点切换 FSDB

- **日期**：2026-09-19
- **标签**：VCS · Verdi · FSDB · SystemVerilog · 仿真调试
- **数据**：[`data/results.csv`](data/results.csv)、[`data/simulation-excerpt.log`](data/simulation-excerpt.log)
- **复现脚本**：[`bench/`](bench/)

## TL;DR

- 用 `$fsdbSwitchDumpfile(filename)` 在当前任务真正完成、下一个任务开始之前切换文件，边界不需要预先换算成仿真时间。
- 在 VCS/Verdi X-2025.06 上跑了两组不同任务长度，8 个分段文件全部通过时间范围、起始值和参考波形检查。对 70 个时间点上的 4 个信号进行了比较。
- 分段后沿用原仿真的绝对时间，DUT 状态继续运行。本例中，新文件保留了从未变化的 `held_value`，不需要等待信号再次跳变才能看到值。
- 本机的旧式 `-P novas.tab pli.a` 配置导致 FSDB dumper 报错；使用正确的 `VERDI_HOME` 和 `-debug_access+all` 后成功。
- 按任务切分解决的是调试边界问题，不保证每段等大，也不代表总磁盘占用会下降。

## 1. 背景：需要的是任务边界

长时间仿真可能依次执行初始化、配置、数据传输、回读等任务。如果所有阶段写进一个大波形文件，定位某个任务不方便。

理想的分段方式是：初始化结束时开 A 的波形，A 完成时开 B 的波形，B 完成时开 C 的波形。各任务耗时可以变化，分段逻辑应跟随完成条件，而不是写死 `#10000`。

VCS 执行 testbench 中的控制逻辑，FSDB dumper 执行文件切换；任务边界的语义由验证环境提供。

## 2. 环境与验证范围

| 项目 | 本次配置 |
|---|---|
| 系统 | Rocky Linux 8.10，x86_64 |
| 仿真器 | VCS X-2025.06_Full64 |
| 波形工具 | Verdi X-2025.06，`fsdb2vcd` X-2025.06 |
| testbench | 独立的 SystemVerilog module，不依赖业务 RTL 或 UVM |
| 时间单位 / 精度 | 1 ns / 1 ps |
| 时钟 | 周期 10 ns，计数器在上升沿用 NBA 更新 |
| 校验方式 | 将各 FSDB 转成 VCD，与同次仿真生成的完整 VCD 比较 |

本次验证的是按任务切换 FSDB 的功能正确性。没有进行 GB 级文件、性能、UVM 集成、多文件流、glitch/delta-cycle 保留或 VPD 的实测。公开附件仅包含独立示例、检查脚本及其结果。

## 3. 最小用法

以下片段放入已有 testbench；任务名需要替换为工程中的实际实现。完整可运行例子见 [`tb_wave_split.sv`](bench/tb_wave_split.sv)。

```systemverilog
initial begin
    $fsdbDumpfile("00_init.fsdb");
    $fsdbDumpvars(0, tb_top);

    reset_and_init();

    $fsdbSwitchDumpfile("01_task_a.fsdb");
    run_task_a();
    wait_task_a_complete();

    $fsdbSwitchDumpfile("02_task_b.fsdb");
    run_task_b();
    wait_task_b_complete();

    $finish;
end
```

如果 `run_task_a()` 本身已等待所有响应和检查完成，就不需要重复等待。切换前不必先 `$fsdbDumpoff`，本例也没有在每次切换后重复 `$fsdbDumpvars`。

### 统一封装命名和切换

```systemverilog
int unsigned wave_index = 0;

task automatic next_wave(input string task_name);
    string filename;
    wave_index++;
    filename = $sformatf("%04d_%s.fsdb", wave_index, task_name);
    $fsdbSwitchDumpfile(filename);
    $display("[%0t] Waveform switched to %s", $time, filename);
endtask
```

先完成一次 `$fsdbDumpfile` / `$fsdbDumpvars` 初始化，再调用封装。由一个控制线程串行调用，任务名使用适合文件名的短字符串。每次仿真使用独立输出目录，防止不同测试或重复运行覆盖同名波形。

如果同时打开多条 FSDB 输出流，应显式指定要切换的源文件，而不是依赖隐含的活动文件选择：

```systemverilog
$fsdbSwitchDumpfile("next.fsdb", "+fsdbfile+current.fsdb");
```

这条多文件语法来自工具手册，本次只验证了单条输出流。

## 4. 完成条件比切换接口更重要

发送函数返回，可能只表示请求已经交给 driver；DUT 仍在处理，response 和 scoreboard 检查尚未完成。此时立即切换，会把同一个任务的请求与响应放进不同文件。

建议明确写出完成条件，例如：该任务的全部响应已收齐、对应 outstanding 计数归零、相关检查已完成。在 UVM 中，`seq.start()` 返回是否代表这些条件成立，取决于 driver 和 response 的约定。

并行环境可以用下面的控制顺序：

```text
等待任务 A 完成确认
        ↓
统一控制线程切换波形
        ↓
统一控制线程启动 / 放行任务 B
```

如果一个线程监听 A 完成后切文件，另一个线程同时开始 B，则同一时刻的调度顺序可能产生竞争。跨线程控制可以使用 mailbox 或带确认的握手；裸 event 还要注意监听者是否已经进入等待。

本次例子在最后一个有效上升沿后的下降沿返回，确保对应计数器的 NBA 更新已经完成。这是示例的同步规则，不是所有协议都应额外等半拍。实际工程应使用自身的采样和完成规则，不能靠随意加入 `#0` 保证 NBA 已完成。

## 5. 实验方法与结果

初始化固定占两个时钟周期。三个任务分别等待给定数量的上升沿，再在随后下降沿返回。切换函数只在任务返回后调用，不包含预设切换时刻。

| 用例 | A / B / C 周期数 | 初始化区间（ns） | A 区间（ns） | B 区间（ns） | C 区间（ns） |
|---|---|---|---|---|---|
| case1 | 3 / 7 / 4 | 0–20 | 20–50 | 50–120 | 120–160 |
| case2 | 6 / 2 / 9 | 0–20 | 20–80 | 80–100 | 100–190 |

表中的时间来自实际输出，不是写入切换逻辑的条件。仅改变任务长度，B 的开始时刻从 50 ns 变为 80 ns，C 的开始时刻从 120 ns 变为 100 ns。

每次仿真生成四个 FSDB：

```text
00_init.fsdb
01_task_a.fsdb
02_task_b.fsdb
03_task_c.fsdb
```

检查脚本完成以下验证：

1. 用 `fsdb2vcd -summary` 确认每段文件已完成、开始和结束时间符合任务周期数。
2. 检查新文件起点的 `counter`、`phase_id` 和 `held_value`。其中 `held_value = 32'hcafe1234` 在整个仿真中不变化，用于验证新段包含初值。
3. 将每段转成 VCD，在分段和参考文件时间戳的并集上，比较 `[start, end)` 内的 `clk`、`counter`、`phase_id`、`held_value`。
4. 额外检查每段结束时的计数器值。

最终输出：

```text
WAVE_CHECK_PASS files=8 timestamps=70 signals_per_timestamp=4
```

case1 最终计数器为 16，case2 为 19，与初始化及任务周期数之和一致。逐文件时间范围、文件大小及检查数量保存在 [`results.csv`](data/results.csv)。

### 相邻文件可能包含同一个边界时间戳

例如，case1 的 A 文件结束于 50 ns，B 文件开始于 50 ns。文件时间范围可以共享端点，不能把它理解为严格互不重叠的时间戳集合。

检查器使用 `[start, end)` 比较阶段内的稳定值，并单独检查结束计数器。它没有验证同一时间戳内所有 delta-cycle 的变化顺序；需要这种精度时，应按工具的 glitch/delta 记录设置另做验证。

## 6. 编译与复现

先在已安装、已授权的环境配置 `VCS_HOME`、`VERDI_HOME`、`PATH` 和许可证。本文测试的编译方式为：

```bash
vcs -full64 -sverilog -debug_access+all \
  tb_wave_split.sv -top tb_wave_split -o simv -l compile.log
./simv +A=3 +B=7 +C=4 -l sim.log
```

运行完整两组实验及校验：

```bash
cd posts/2026-09-19-vcs-task-boundary-waveform-splitting
bash bench/run.sh
```

脚本在当前目录创建唯一的 `wave-split-run.XXXXXX` 输出目录，包含编译日志、两组仿真日志、FSDB、转换后的 VCD、时间摘要和 `results.csv`。需要 Python 3，检查器只使用标准库。

完整参考 VCD 只为这个小实验提供校验依据。大规模工程正常使用分段 FSDB 时，不需要额外生成它。

### 本次遇到的版本问题

首次尝试显式加入旧式 `-P novas.tab pli.a` 后出现重复系统任务定义警告，运行时 FSDB dumper 报错，提示该方式从 Verdi 2024.09 起弃用，要求使用 `-debug_access` 配合正确的 `VERDI_HOME`。

移除旧式 `-P` 参数后，本次 X-2025.06 环境正常加载 dumper 并生成分段文件。旧版工具是否需要其他接入方式，应查对应版本手册，不能把这条新版本配置推广到所有版本。

这次还说明：testbench 打印 `SIM_PASS` 只能说明它执行到了结束位置，不能证明波形成功生成。因此脚本同时检查 dumper 错误、文件数量和实际波形内容。

## 7. 几种控制方式不要混用概念

| 需求 | 接口 / 方法 | 注意点 |
|---|---|---|
| 按任务完成节点分段 | `$fsdbSwitchDumpfile` | 本文已实测；任务完成由 testbench 定义 |
| 按大小自动分段 | `$fsdbAutoSwitchDumpfile` | 本文未实测；不自动理解任务边界 |
| 暂停 / 恢复记录 | `$fsdbDumpoff` / `$fsdbDumpon` | 控制记录区间，本身不是换文件 |
| 刷新缓冲到文件 | `$fsdbDumpflush` | 不等于创建新段 |
| 限制单个文件大小 | `$fsdbDumpfile` 的大小参数 | X-2025.06 手册说明采用滑动窗口，可能丢弃旧值，不适合当成完整历史分段 |

X-2025.06 手册还列出了按墙钟时间或仿真时间周期自动切换的模式。有限文件数的自动切换涉及覆盖 / 停止策略，使用时要检查对应版本说明。

如果单个任务自身仍然很大，可以先减少 dump 层级或信号范围，或把任务内部进一步划成有意义的子阶段。手动切换与自动大小切换组合的行为，本次未验证。

### 如果输出的是 VPD

VCS 手册给出的文件切换流程可写成：

```systemverilog
// 当前任务已完成，下一任务尚未开始
$vcdplusclose;
$vcdplusfile("02_task_b.vpd");
$vcdpluson(0, tb_top);
```

`$vcdplusclose` 会结束记录并重置设置；新段需要重新启用所需记录，额外 memory 等配置也应相应恢复。这部分依据 VCS 文档整理，未在本次实验中运行。

## 8. 结论与局限

按业务节点分割波形，可以把“完成确认 → 切换文件 → 下一任务开始”放进统一的仿真控制流程。这样任务耗时变化时，波形边界也会自动跟随。

本次验证支持单条 FSDB 输出流在任务边界切换，并保留所检查信号的初值与阶段内稳定值。样例文件很小，结果不能用于推断 GB 级波形的速度、内存占用或压缩比。分段会重复存储部分结构和初值，目标是便于按阶段读取，而不是保证更小的总文件体积。

## 参考

- 本机 Verdi X-2025.06 安装手册：`$VERDI_HOME/doc/verdi_linking_dumping.pdf`，`$fsdbDumpfile`、`$fsdbAutoSwitchDumpfile`、`$fsdbSwitchDumpfile` 条目。本文核对了该版本接口，没有将厂商手册复制进仓库。
- [FSDB dumping 手册公开转载版](https://www.scribd.com/document/857847528/Linking-Dumping)：便于查阅通用接口；具体行为优先以安装版本文档为准。
- [VCS/VCSi User Guide，大学站点存档](https://users.ece.utexas.edu/~patt/10s.382N/handouts/vcs.pdf)：VPD 系统任务说明；该存档属于旧版文档。
