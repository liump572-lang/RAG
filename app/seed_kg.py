from app.database import SessionLocal
from app.modules.kg.service import KgService

KG_DATA = {
    1: {
        "nodes": [
            ("计算机网络概述", None, 2),
            ("OSI七层模型", "开放系统互连参考模型", 2),
            ("TCP/IP协议栈", "事实上的工业标准", 2),
            ("物理层", "传输比特流", 3),
            ("数据链路层", "帧传输与差错控制", 3),
            ("网络层", "路由与IP寻址", 2),
            ("传输层", "端到端可靠传输", 2),
            ("应用层", "网络应用协议", 3),
            ("IP地址与子网", "IPv4地址分类与子网划分", 3),
            ("TCP协议", "面向连接的可靠传输", 2),
            ("UDP协议", "无连接的不可靠传输", 3),
            ("路由协议", "RIP、OSPF、BGP", 4),
            ("HTTP协议", "超文本传输协议", 3),
            ("DNS系统", "域名解析系统", 3),
        ],
        "edges": [
            (1, 2, "CONTAINS"), (1, 3, "CONTAINS"),
            (2, 4, "NEXT"), (4, 5, "NEXT"), (5, 6, "NEXT"),
            (6, 7, "NEXT"), (7, 8, "NEXT"),
            (3, 5, "RELATED"), (3, 6, "RELATED"), (3, 7, "RELATED"),
            (6, 9, "CONTAINS"), (7, 10, "CONTAINS"), (7, 11, "CONTAINS"),
            (6, 12, "CONTAINS"), (10, 11, "CONTRAST"),
            (8, 13, "CONTAINS"), (8, 14, "CONTAINS"),
            (10, 2, "EXAMINED_IN"),
        ],
    },
    2: {
        "nodes": [
            ("操作系统概述", None, 2),
            ("进程管理", "进程的概念与调度", 2),
            ("内存管理", "内存分配与虚拟内存", 2),
            ("文件系统", "文件存储与管理", 3),
            ("设备管理", "I/O设备与驱动", 3),
            ("死锁", "死锁的产生与处理", 3),
            ("进程调度算法", "FCFS、SJF、RR等", 3),
            ("页面置换算法", "FIFO、LRU、OPT等", 4),
            ("进程同步", "PV操作与管程", 3),
        ],
        "edges": [
            (1, 2, "CONTAINS"), (1, 3, "CONTAINS"),
            (1, 4, "CONTAINS"), (1, 5, "CONTAINS"),
            (2, 6, "RELATED"), (2, 7, "CONTAINS"),
            (2, 9, "CONTAINS"), (3, 8, "CONTAINS"),
            (2, 9, "PREREQUISITE"),
        ],
    },
    4: {
        "nodes": [
            ("计算机系统概论", None, 1),
            ("数据表示", "原码、反码、补码、浮点数", 3),
            ("运算器与ALU", "算术逻辑单元", 3),
            ("存储器层次结构", "Cache、主存、辅存", 2),
            ("指令系统", "指令格式与寻址方式", 3),
            ("CPU设计", "数据通路与控制单元", 4),
            ("总线系统", "系统总线与通信", 3),
            ("输入输出系统", "中断、DMA、通道", 3),
            ("流水线技术", "指令流水线与冒险", 4),
        ],
        "edges": [
            (1, 2, "NEXT"), (1, 3, "NEXT"), (1, 4, "NEXT"),
            (1, 5, "NEXT"), (5, 6, "NEXT"), (6, 9, "NEXT"),
            (4, 8, "RELATED"), (6, 7, "RELATED"),
        ],
    },
}


def seed_kg():
    db = SessionLocal()
    name_to_id = {}

    for subject_id, data in KG_DATA.items():
        print(f"\n=== Subject {subject_id} ===")

        for node_name, desc, diff in data["nodes"]:
            try:
                point = KgService.create_point(db, node_name, subject_id, desc, diff)
                name_to_id[f"{subject_id}:{node_name}"] = point.id
                print(f"  Node: {node_name}")
            except Exception as e:
                print(f"  Error creating {node_name}: {e}")

        for src_idx, tgt_idx, rel_type in data["edges"]:
            src_name = data["nodes"][src_idx - 1][0]
            tgt_name = data["nodes"][tgt_idx - 1][0]
            src_id = name_to_id.get(f"{subject_id}:{src_name}")
            tgt_id = name_to_id.get(f"{subject_id}:{tgt_name}")
            if src_id and tgt_id:
                try:
                    KgService.create_relation(db, src_id, tgt_id, rel_type)
                    print(f"  Edge: {src_name} -[{rel_type}]-> {tgt_name}")
                except Exception as e:
                    print(f"  Error: {e}")

    db.close()
    print("\n知识图谱种子数据已就绪！")


if __name__ == "__main__":
    seed_kg()
