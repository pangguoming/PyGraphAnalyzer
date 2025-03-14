# PyGraphAnalyzer

PyGraphAnalyzer 是一个用于分析 Python 项目代码结构的工具，能够生成 Cypher 语句来表示函数调用关系，并将其可视化在图数据库中。

## 功能特性

- 解析 Python 项目中的函数定义
- 分析函数之间的调用关系
- 生成 Cypher 语句用于图数据库
- 支持将结果保存到文件

## 使用说明

1. 克隆本仓库
   ```bash
   git clone https://github.com/yourusername/pygraphanalyzer.git
   ```
2. 安装依赖
3. 运行分析工具
4. 查看输出结果
   
   - 生成的 Cypher 语句会保存在 output.cypher 文件中
   - 可以在 Neo4j 等图数据库中导入这些 Cypher 语句
## 配置选项
- project_path : 要分析的 Python 项目路径
- output_file : Cypher 语句输出文件路径
## 示例输出
```cypher
CREATE (f:PythonFile {path: 'D:\\PythonWorkspace\\project\\main.py'});
CREATE (fn:PythonFunction {name: 'main', line_number: 10});
MATCH (f:PythonFile {path: 'D:\\PythonWorkspace\\project\\main.py'}), (fn:PythonFunction {name: 'main'})
CREATE (fn)-[:DEFINED_IN]->(f);
```

## 贡献指南
欢迎提交 Pull Request 或 Issue 来改进本项目。

## 许可证
MIT License