import os
import ast
from collections import defaultdict

class PythonFunctionVisitor(ast.NodeVisitor):
    def __init__(self, file_path):
        self.file_path = file_path
        self.calls = []
        self.current_func = None
        self.functions = {}  # 改为字典，存储函数名和行号

    def visit_FunctionDef(self, node):
        self.current_func = node.name
        self.functions[node.name] = node.lineno  # 存储函数名和行号
        self.generic_visit(node)

    def visit_Call(self, node):
        if self.current_func:
            if isinstance(node.func, ast.Name):
                called_func = node.func.id
                call_line = node.lineno
                self.calls.append((self.current_func, called_func, call_line))
        self.generic_visit(node)

def analyze_python_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        tree = ast.parse(code)
        visitor = PythonFunctionVisitor(file_path)
        visitor.visit(tree)
        return visitor.calls, visitor.functions  # 直接返回字典
    except Exception as e:
        print(f"Error analyzing {file_path}: {str(e)}")
        return [], {}  # 返回空字典而不是集合

def generate_cypher(functions, calls):
    cypher_commands = []
    file_nodes = set()
    
    # 创建文件节点
    for file_path, _ in set(functions.values()):  # 解包元组，获取file_path
        file_nodes.add(file_path)
        # 将路径中的单反斜杠替换为双反斜杠
        safe_path = file_path.replace('\\', '\\\\')
        cypher_commands.append(
            f"CREATE (f:PythonFile {{path: '{safe_path}'}});\n"
        )
    
    # 创建函数节点并关联到文件
    for func, (file_path, line_number) in functions.items():
        # 将路径中的单反斜杠替换为双反斜杠
        safe_path = file_path.replace('\\', '\\\\')
        cypher_commands.append(
            f"CREATE (fn:PythonFunction {{name: '{func}', line_number: {line_number}}});\n"
            f"MATCH (f:PythonFile {{path: '{safe_path}'}}), (fn:PythonFunction {{name: '{func}'}})\n"
            f"CREATE (fn)-[:DEFINED_IN]->(f);\n"
        )
    
    # 创建调用关系
    for caller, callee, line in calls:
        cypher_commands.append(
            f"MATCH (a:PythonFunction {{name: '{caller}'}}), (b:PythonFunction {{name: '{callee}'}})\n"
            f"CREATE (a)-[:CALLS {{line: {line}}}]->(b);\n"
        )
    
    return cypher_commands

def analyze_python_project(project_path):
    functions = {}
    calls = []
    
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                file_calls, file_functions = analyze_python_file(file_path)
                calls.extend(file_calls)
                
                # 修改存储方式，同时保存文件路径和行号
                for func, line_number in file_functions.items():
                    functions[func] = (file_path, line_number)
    
    return generate_cypher(functions, calls)

if __name__ == "__main__":
    project_path = "D:\\PythonWorkspace\\OpenManus-main"  # 修改为你的Python项目路径
    cypher_commands = analyze_python_project(project_path)
    
    # 将Cypher语句保存到文件
    output_file = "D:\\PythonWorkspace\\OpenManus-main\\output.cypher"
    with open(output_file, 'w', encoding='utf-8') as f:
        for command in cypher_commands:
            f.write(command)
    
    print(f"Cypher语句已保存到 {output_file}")