`timescale 1ns/1ps
module tb_wave_split;
  bit clk = 0;
  int unsigned counter = 0;
  int unsigned phase_id = 0;
  logic [31:0] held_value = 32'hcafe1234;
  int cycles_a = 3, cycles_b = 7, cycles_c = 4;
  int manifest;
  int unsigned segment = 0;
  string filename;

  always #5 clk = ~clk;
  always @(posedge clk) counter <= counter + 1;

  task automatic next_wave(input string name);
    segment++;
    filename = $sformatf("%02d_%s.fsdb", segment, name);
    $fsdbSwitchDumpfile(filename);
    $fdisplay(manifest, "%s,%0t,%0d", filename, $time, counter);
    $display("SWITCH file=%s time=%0t counter=%0d", filename, $time, counter);
  endtask

  // A task returns on a falling edge, after its last rising-edge NBA update.
  // Production environments must use their own response/scoreboard drain rule.
  task automatic run_job(input int id, input int cycles);
    phase_id = id;
    repeat (cycles) @(posedge clk);
    @(negedge clk);
    $display("DONE phase=%0d time=%0t counter=%0d", id, $time, counter);
  endtask

  initial begin
    if ($value$plusargs("A=%d", cycles_a)) begin end
    if ($value$plusargs("B=%d", cycles_b)) begin end
    if ($value$plusargs("C=%d", cycles_c)) begin end
    if (cycles_a < 1 || cycles_b < 1 || cycles_c < 1)
      $fatal(1, "Cycle counts must be positive");
    manifest = $fopen("boundaries.csv", "w");
    if (!manifest) $fatal(1, "Cannot open manifest");
    $fdisplay(manifest, "filename,start_ps,counter_at_switch");
    $dumpfile("reference.vcd");
    $dumpvars(0, tb_wave_split);
    $fsdbDumpfile("00_init.fsdb");
    $fsdbDumpvars(0, tb_wave_split);
    $fdisplay(manifest, "00_init.fsdb,0,0");
    repeat (2) @(negedge clk);
    next_wave("task_a");
    run_job(1, cycles_a);
    next_wave("task_b");
    run_job(2, cycles_b);
    next_wave("task_c");
    run_job(3, cycles_c);
    $fclose(manifest);
    $display("SIM_PASS final_counter=%0d", counter);
    $finish;
  end

  initial begin
    #100000;
    $fatal(1, "Watchdog timeout");
  end
endmodule
