import socket
import struct
import time
import random

# 协议常量
SYN = 1
SYN_ACK = 2
ACK = 3
DATA = 4
FIN = 5

# 丢包率
DROP_RATE = 0.2  # 20%丢包率

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_port = int(input("请输入服务器端口号: "))
server_socket.bind(('', server_port))
print(f"服务器启动，监听端口 {server_port}")

# 连接建立过程
init, addr = server_socket.recvfrom(4)
init_data, client_num = struct.unpack('>HH', init)
if init_data != SYN:
    raise ValueError("连接失败")
print("收到SYN请求")

agree = struct.pack('>HH', SYN_ACK, client_num + 1)  # SYN-ACK=2
server_socket.sendto(agree, addr)
print("发送SYN-ACK响应")

established, addr = server_socket.recvfrom(4)
established_data, ack_num = struct.unpack('>HH', established)
if established_data != ACK or ack_num != client_num + 2:
    raise ValueError("确认连接信号失败")
print("收到ACK完成三次握手")
print(f"与 {addr} 建立连接成功\n")

# 数据传输
expected_seq = 0  #期望接收的序列号
ack_num=-1#ack初始值

while True:
    data, addr = server_socket.recvfrom(80)

    # 检查是否是FIN包
    header = data[:4]
    pkt_type, seq_num = struct.unpack('>HH', header)
    if pkt_type == FIN:
        print("收到FIN包，连接关闭")
        break

    # 模拟丢包
    if random.random() < DROP_RATE:
        print(f"模拟丢包: 第{seq_num}个包")
        continue

    # 只处理期望的序列号
    if seq_num == expected_seq:
        # 累积确认
        ack_num = expected_seq
        res = struct.pack('>HhI', ACK, ack_num, int(time.time()))
        server_socket.sendto(res, addr)
        print(f"发送ACK: {ack_num}")
        expected_seq += 1
    else:
        # 对于乱序到达的包，发送上一个ACK
        res = struct.pack('>HhI', ACK, ack_num, int(time.time()))
        server_socket.sendto(res, addr)
        print(f"收到乱序包 {seq_num}, 发送上一个ACK: {ack_num}")

server_socket.close()