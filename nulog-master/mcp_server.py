#!/usr/bin/env python3
"""
MCP Server for NuLog Log Parser
Provides tools for parsing logs using the NuLog model
"""

import os
import tempfile
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastmcp import FastMCP
from NuLog import LogParser
import pandas as pd

# 从 benchmark.py 中提取的配置
BENCHMARK_SETTINGS = {
    "BGL": {
        "log_file": "BGL/BGL_2k.log",
        "log_format": "<Label> <Timestamp> <Date> <Node> <Time> <NodeRepeat> <Type> <Component> <Level> <Content>",
        "filters": "([ |:|\(|\)|=|,])|(core.)|(\.{2,})",
        "k": 50,
        "nr_epochs": 3,
        "num_samples": 0,
    },
    "Android": {
        "log_file": "Android/Android_2k.log",
        "log_format": "<Date> <Time>  <Pid>  <Tid> <Level> <Component>: <Content>",
        "filters": '([ |:|\(|\)|=|,|"|\{|\}|@|$|\[|\]|\||;])',
        "k": 25,
        "nr_epochs": 5,
        "num_samples": 5000,
    },
    "OpenStack": {
        "log_file": "OpenStack/OpenStack_2k.log",
        "log_format": "<Logrecord> <Date> <Time> <Pid> <Level> <Component> \[<ADDR>\] <Content>",
        "filters": '([ |:|\(|\)|"|\{|\}|@|$|\[|\]|\||;])',
        "k": 5,
        "nr_epochs": 6,
        "num_samples": 0,
    },
    "HDFS": {
        "log_file": "HDFS/HDFS_2k.log",
        "log_format": "<Date> <Time> <Pid> <Level> <Component>: <Content>",
        "filters": "(\s+blk_)|(:)|(\s)",
        "k": 15,
        "nr_epochs": 5,
        "num_samples": 0,
    },
    "Apache": {
        "log_file": "Apache/Apache_2k.log",
        "log_format": "\[<Time>\] \[<Level>\] <Content>",
        "filters": "([ ])",
        "k": 12,
        "nr_epochs": 5,
        "num_samples": 0,
    },
    "HPC": {
        "log_file": "HPC/HPC_2k.log",
        "log_format": "<LogId> <Node> <Component> <State> <Time> <Flag> <Content>",
        "filters": "([ |=])",
        "num_samples": 0,
        "k": 10,
        "nr_epochs": 3,
    },
    "Windows": {
        "log_file": "Windows/Windows_2k.log",
        "log_format": "<Date> <Time>, <Level>                  <Component>    <Content>",
        "filters": "([ ])",
        "num_samples": 0,
        "k": 95,
        "nr_epochs": 5,
    },
    "HealthApp": {
        "log_file": "HealthApp/HealthApp_2k.log",
        "log_format": "<Time>\|<Component>\|<Pid>\|<Content>",
        "filters": "([ ])",
        "num_samples": 0,
        "k": 100,
        "nr_epochs": 5,
    },
    "Mac": {
        "log_file": "Mac/Mac_2k.log",
        "log_format": "<Month>  <Date> <Time> <User> <Component>\[<PID>\]( \(<Address>\))?: <Content>",
        "filters": "([ ])|([\w-]+\.){2,}[\w-]+",
        "num_samples": 0,
        "k": 300,
        "nr_epochs": 10,
    },
    "Spark": {
        "log_file": "Spark/Spark_2k.log",
        "log_format": "<Date> <Time> <Level> <Component>: <Content>",
        "filters": "([ ])|(\d+\sB)|(\d+\sKB)|(\d+\.){3}\d+|\b[KGTM]?B\b|([\w-]+\.){2,}[\w-]+",
        "num_samples": 0,
        "k": 50,
        "nr_epochs": 3,
    },
}

# 创建 MCP 应用
mcp = FastMCP("NuLog Parser")


def _read_parsed_results(output_dir: str, log_name: str, limit: int = 100) -> Dict[str, Any]:
    """读取解析结果文件并返回结构化数据"""
    result_file = os.path.join(output_dir, f"{log_name}_structured.csv")
    if not os.path.exists(result_file):
        return {"templates": [], "count": 0}
    
    try:
        df = pd.read_csv(result_file)
        # 限制返回的记录数
        df_limited = df.head(limit)
        
        templates = []
        for _, row in df_limited.iterrows():
            templates.append({
                "EventId": str(row.get("EventId", "")),
                "EventTemplate": str(row.get("EventTemplate", ""))
            })
        
        return {
            "templates": templates,
            "count": len(df),
            "returned_count": len(templates)
        }
    except Exception as e:
        return {"error": f"读取结果文件失败: {str(e)}", "templates": [], "count": 0}


@mcp.tool()
def parse_log(
    log_content: str,
    log_format: str,
    filters: str = "([ |:|\(|\)|=|,])|(core.)|(\.{2,})",
    k: int = 50,
    nr_epochs: int = 3,
    num_samples: int = 0,
    batch_size: int = 5,
    pad_len: int = 150,
    limit: int = 100
) -> Dict[str, Any]:
    """
    解析日志内容字符串
    
    Args:
        log_content: 日志内容字符串（多行文本）
        log_format: 日志格式，例如: "<Date> <Time> <Pid> <Level> <Component>: <Content>"
        filters: 正则表达式过滤器，用于tokenization
        k: top-k 参数，用于模板提取
        nr_epochs: 训练轮数
        num_samples: 采样数量（0表示使用全部数据）
        batch_size: 批次大小
        pad_len: 序列填充长度
        limit: 返回结果的最大数量
    
    Returns:
        包含解析结果的字典，包括模板列表和统计信息
    """
    temp_dir = None
    temp_file = None
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="nulog_parse_")
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # 将日志内容写入临时文件
        log_file_name = "temp_log.log"
        temp_file = os.path.join(temp_dir, log_file_name)
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(log_content)
        
        # 创建解析器并解析
        parser = LogParser(
            indir=temp_dir,
            outdir=output_dir,
            filters=filters,
            k=k,
            log_format=log_format
        )
        
        parser.parse(
            log_file_name,
            batch_size=batch_size,
            pad_len=pad_len,
            nr_epochs=nr_epochs,
            num_samples=num_samples
        )
        
        # 读取解析结果
        result = _read_parsed_results(output_dir, log_file_name.split(".")[0], limit)
        result["status"] = "success"
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"解析日志时出错: {str(e)}",
            "templates": []
        }
    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass


@mcp.tool()
def parse_log_file(
    file_path: str,
    log_format: str,
    filters: str = "([ |:|\(|\)|=|,])|(core.)|(\.{2,})",
    k: int = 50,
    nr_epochs: int = 3,
    num_samples: int = 0,
    batch_size: int = 5,
    pad_len: int = 150,
    output_dir: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    解析磁盘上的日志文件
    
    Args:
        file_path: 日志文件的路径
        log_format: 日志格式，例如: "<Date> <Time> <Pid> <Level> <Component>: <Content>"
        filters: 正则表达式过滤器，用于tokenization
        k: top-k 参数，用于模板提取
        nr_epochs: 训练轮数
        num_samples: 采样数量（0表示使用全部数据）
        batch_size: 批次大小
        pad_len: 序列填充长度
        output_dir: 输出目录（如果为None，则使用临时目录）
        limit: 返回结果的最大数量
    
    Returns:
        包含解析结果的字典，包括模板列表和统计信息
    """
    temp_dir = None
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "error": f"文件不存在: {file_path}",
                "templates": []
            }
        
        # 确定输入和输出目录
        input_dir = os.path.dirname(os.path.abspath(file_path))
        log_file_name = os.path.basename(file_path)
        
        if output_dir is None:
            temp_dir = tempfile.mkdtemp(prefix="nulog_parse_file_")
            output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建解析器并解析
        parser = LogParser(
            indir=input_dir,
            outdir=output_dir,
            filters=filters,
            k=k,
            log_format=log_format
        )
        
        parser.parse(
            log_file_name,
            batch_size=batch_size,
            pad_len=pad_len,
            nr_epochs=nr_epochs,
            num_samples=num_samples
        )
        
        # 读取解析结果
        base_name = os.path.splitext(log_file_name)[0]
        result = _read_parsed_results(output_dir, base_name, limit)
        result["status"] = "success"
        result["output_dir"] = output_dir
        if temp_dir:
            result["note"] = f"结果保存在临时目录: {output_dir}，请手动清理"
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"解析日志文件时出错: {str(e)}",
            "templates": []
        }


@mcp.tool()
def benchmark_dataset(
    dataset_name: str,
    input_dir: str,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    运行基准测试
    
    Args:
        dataset_name: 数据集名称（BGL, HDFS, Android, OpenStack, Apache, HPC, Windows, HealthApp, Mac, Spark）
        input_dir: 输入目录路径
        output_dir: 输出目录路径（如果为None，则使用临时目录）
    
    Returns:
        包含F1分数和准确率的字典
    """
    if dataset_name not in BENCHMARK_SETTINGS:
        available_datasets = ", ".join(BENCHMARK_SETTINGS.keys())
        return {
            "status": "error",
            "error": f"不支持的数据集: {dataset_name}。支持的数据集: {available_datasets}",
            "f1_score": None,
            "accuracy": None
        }
    
    setting = BENCHMARK_SETTINGS[dataset_name]
    temp_dir = None
    
    try:
        # 确定输出目录
        if output_dir is None:
            temp_dir = tempfile.mkdtemp(prefix="nulog_benchmark_")
            output_dir = temp_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 确定输入目录和日志文件
        log_file_path = os.path.join(input_dir, setting["log_file"])
        if not os.path.exists(log_file_path):
            return {
                "status": "error",
                "error": f"日志文件不存在: {log_file_path}",
                "f1_score": None,
                "accuracy": None
            }
        
        indir = os.path.join(input_dir, os.path.dirname(setting["log_file"]))
        log_file = os.path.basename(setting["log_file"])
        
        # 创建解析器并解析
        parser = LogParser(
            indir=indir,
            outdir=output_dir,
            filters=setting["filters"],
            k=setting["k"],
            log_format=setting["log_format"]
        )
        
        parser.parse(
            log_file,
            nr_epochs=setting["nr_epochs"],
            num_samples=setting["num_samples"]
        )
        
        # 尝试评估结果（如果 groundtruth 文件存在）
        groundtruth_file = os.path.join(indir, log_file + "_structured.csv")
        parsed_result_file = os.path.join(output_dir, log_file + "_structured.csv")
        
        result = {
            "status": "success",
            "dataset": dataset_name,
            "output_dir": output_dir,
            "parsed_result_file": parsed_result_file
        }
        
        note = None
        # 如果 groundtruth 文件存在，尝试计算指标
        if os.path.exists(groundtruth_file) and os.path.exists(parsed_result_file):
            try:
                # 简单的准确率计算（如果没有 evaluator 模块）
                df_groundtruth = pd.read_csv(groundtruth_file)
                df_parsed = pd.read_csv(parsed_result_file)
                
                # 基于 EventTemplate 的简单匹配
                groundtruth_templates = set(df_groundtruth.get("EventTemplate", []).astype(str))
                parsed_templates = set(df_parsed.get("EventTemplate", []).astype(str))
                
                if len(groundtruth_templates) > 0:
                    accuracy = len(groundtruth_templates & parsed_templates) / len(groundtruth_templates)
                    result["accuracy"] = float(accuracy)
                    result["f1_score"] = None  # 需要更复杂的计算，暂时为 None
                    note = "仅计算了基于模板的准确率，F1分数需要evaluator模块"
                else:
                    result["accuracy"] = None
                    result["f1_score"] = None
                    note = "无法计算指标：groundtruth文件为空"
            except Exception as e:
                result["accuracy"] = None
                result["f1_score"] = None
                result["evaluation_error"] = str(e)
                note = "评估指标计算失败，但解析已完成"
        else:
            result["accuracy"] = None
            result["f1_score"] = None
            note = "groundtruth文件不存在，跳过评估"
        
        # 如果使用了临时目录，添加到 note 中
        if temp_dir:
            temp_note = f"结果保存在临时目录: {output_dir}，请手动清理"
            note = (note + " " + temp_note) if note else temp_note
        
        if note:
            result["note"] = note
        
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"基准测试失败: {str(e)}",
            "f1_score": None,
            "accuracy": None
        }
    # 注意：如果 output_dir 由用户指定，则不清理临时目录


@mcp.tool()
def get_supported_formats() -> Dict[str, Any]:
    """
    获取支持的日志格式列表
    
    Returns:
        包含所有支持的日志格式配置的字典
    """
    formats_info = {}
    for dataset_name, setting in BENCHMARK_SETTINGS.items():
        formats_info[dataset_name] = {
            "log_format": setting["log_format"],
            "filters": setting["filters"],
            "k": setting["k"],
            "nr_epochs": setting["nr_epochs"],
            "num_samples": setting["num_samples"]
        }
    
    return {
        "status": "success",
        "supported_datasets": list(BENCHMARK_SETTINGS.keys()),
        "formats": formats_info
    }


if __name__ == "__main__":
    mcp.run(transport="sse", host="127.0.0.1", port=4005)

