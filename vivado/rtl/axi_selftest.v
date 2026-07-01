`timescale 1 ns / 1 ps

module axi_selftest #
(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 4
)
(
    input wire s_axi_aclk,
    input wire s_axi_aresetn,
    input wire [C_S_AXI_ADDR_WIDTH-1:0] s_axi_awaddr,
    input wire [2:0] s_axi_awprot,
    input wire s_axi_awvalid,
    output reg s_axi_awready,
    input wire [C_S_AXI_DATA_WIDTH-1:0] s_axi_wdata,
    input wire [(C_S_AXI_DATA_WIDTH/8)-1:0] s_axi_wstrb,
    input wire s_axi_wvalid,
    output reg s_axi_wready,
    output reg [1:0] s_axi_bresp,
    output reg s_axi_bvalid,
    input wire s_axi_bready,
    input wire [C_S_AXI_ADDR_WIDTH-1:0] s_axi_araddr,
    input wire [2:0] s_axi_arprot,
    input wire s_axi_arvalid,
    output reg s_axi_arready,
    output reg [C_S_AXI_DATA_WIDTH-1:0] s_axi_rdata,
    output reg [1:0] s_axi_rresp,
    output reg s_axi_rvalid,
    input wire s_axi_rready
);

localparam integer ADDR_LSB = 2;
localparam integer REG_SCRATCH = 0;
localparam integer REG_ID = 1;
localparam integer REG_COUNTER = 2;

reg [31:0] scratch_reg;
reg [31:0] counter_reg;
reg [C_S_AXI_ADDR_WIDTH-1:0] axi_awaddr;
reg [C_S_AXI_ADDR_WIDTH-1:0] axi_araddr;
reg [C_S_AXI_DATA_WIDTH-1:0] axi_wdata;
reg [(C_S_AXI_DATA_WIDTH/8)-1:0] axi_wstrb;
reg aw_seen;
reg w_seen;
integer byte_index;

wire write_fire = aw_seen && w_seen && !s_axi_bvalid;
wire read_fire = s_axi_arready && s_axi_arvalid;
wire [1:0] write_addr = axi_awaddr[ADDR_LSB+1:ADDR_LSB];
wire [1:0] read_addr = axi_araddr[ADDR_LSB+1:ADDR_LSB];

always @(posedge s_axi_aclk) begin
    if (!s_axi_aresetn) begin
        counter_reg <= 32'd0;
    end else begin
        counter_reg <= counter_reg + 1'b1;
    end
end

always @(posedge s_axi_aclk) begin
    if (!s_axi_aresetn) begin
        s_axi_awready <= 1'b0;
        axi_awaddr <= {C_S_AXI_ADDR_WIDTH{1'b0}};
        aw_seen <= 1'b0;
    end else begin
        if (!aw_seen && !s_axi_awready && s_axi_awvalid) begin
            s_axi_awready <= 1'b1;
            axi_awaddr <= s_axi_awaddr;
            aw_seen <= 1'b1;
        end else begin
            s_axi_awready <= 1'b0;
            if (write_fire) aw_seen <= 1'b0;
        end
    end
end

always @(posedge s_axi_aclk) begin
    if (!s_axi_aresetn) begin
        s_axi_wready <= 1'b0;
        axi_wdata <= {C_S_AXI_DATA_WIDTH{1'b0}};
        axi_wstrb <= {(C_S_AXI_DATA_WIDTH/8){1'b0}};
        w_seen <= 1'b0;
    end else begin
        if (!w_seen && !s_axi_wready && s_axi_wvalid) begin
            s_axi_wready <= 1'b1;
            axi_wdata <= s_axi_wdata;
            axi_wstrb <= s_axi_wstrb;
            w_seen <= 1'b1;
        end else begin
            s_axi_wready <= 1'b0;
            if (write_fire) w_seen <= 1'b0;
        end
    end
end

always @(posedge s_axi_aclk) begin
    if (!s_axi_aresetn) begin
        scratch_reg <= 32'd0;
    end else if (write_fire && write_addr == REG_SCRATCH) begin
        for (byte_index = 0; byte_index < 4; byte_index = byte_index + 1) begin
            if (axi_wstrb[byte_index]) begin
                scratch_reg[(byte_index*8) +: 8] <= axi_wdata[(byte_index*8) +: 8];
            end
        end
    end
end

always @(posedge s_axi_aclk) begin
    if (!s_axi_aresetn) begin
        s_axi_bvalid <= 1'b0;
        s_axi_bresp <= 2'b00;
    end else begin
        if (write_fire && !s_axi_bvalid) begin
            s_axi_bvalid <= 1'b1;
            s_axi_bresp <= 2'b00;
        end else if (s_axi_bvalid && s_axi_bready) begin
            s_axi_bvalid <= 1'b0;
        end
    end
end

always @(posedge s_axi_aclk) begin
    if (!s_axi_aresetn) begin
        s_axi_arready <= 1'b0;
        axi_araddr <= {C_S_AXI_ADDR_WIDTH{1'b0}};
    end else begin
        if (!s_axi_arready && s_axi_arvalid) begin
            s_axi_arready <= 1'b1;
            axi_araddr <= s_axi_araddr;
        end else begin
            s_axi_arready <= 1'b0;
        end
    end
end

always @(posedge s_axi_aclk) begin
    if (!s_axi_aresetn) begin
        s_axi_rvalid <= 1'b0;
        s_axi_rresp <= 2'b00;
        s_axi_rdata <= 32'd0;
    end else begin
        if (read_fire && !s_axi_rvalid) begin
            s_axi_rvalid <= 1'b1;
            s_axi_rresp <= 2'b00;
            case (read_addr)
                REG_SCRATCH: s_axi_rdata <= scratch_reg;
                REG_ID: s_axi_rdata <= 32'h50574d31;
                REG_COUNTER: s_axi_rdata <= counter_reg;
                default: s_axi_rdata <= 32'd0;
            endcase
        end else if (s_axi_rvalid && s_axi_rready) begin
            s_axi_rvalid <= 1'b0;
        end
    end
end

endmodule
