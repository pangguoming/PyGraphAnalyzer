import os
import ast
from collections import defaultdict

class PythonFunctionVisitor(ast.NodeVisitor):
    def __init__(self, file_path):
        self.file_path = file_path
        self.calls = []
        self.current_func = None
        self.current_class = None
        self.classes = {}  # 存储类信息
        self.functions = {}
        self.imports = {}  # 新增：存储导入的模块信息

    def visit_Import(self, node):
        # 处理import语句
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        # 处理from ... import语句
        module = node.module
        for alias in node.names:
            self.imports[alias.asname or alias.name] = f"{module}.{alias.name}"
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.current_class = node.name
        # 存储类信息，包括基类和方法
        self.classes[node.name] = {
            'bases': [ast.unparse(base) for base in node.bases],
            'methods': {},
            'static_methods': set(),
            'inherited_methods': set()  # 新增：存储继承的方法
        }
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        self.current_func = node.name
        # 检查方法装饰器
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id == 'classmethod':
                    self.classes[self.current_class]['class_methods'].add(node.name)  # 新增：存储类方法
                elif decorator.id == 'property':
                    self.classes[self.current_class]['properties'].add(node.name)
                elif decorator.id == 'staticmethod':
                    self.classes[self.current_class]['static_methods'].add(node.name)
        
        if self.current_class:
            full_name = f"{self.current_class}.{node.name}"
            self.functions[full_name] = node.lineno
            self.classes[self.current_class]['methods'][node.name] = node.lineno
            # 检查是否重写了父类方法
            for base in self.classes[self.current_class]['bases']:
                if base in self.classes and node.name in self.classes[base]['methods']:
                    self.classes[self.current_class]['inherited_methods'].add(node.name)
        else:
            self.functions[node.name] = node.lineno
        self.generic_visit(node)

    def visit_Call(self, node):
        if self.current_func:
            if isinstance(node.func, ast.Name):
                called_func = node.func.id
                if called_func in self.functions:
                    call_line = node.lineno
                    self.calls.append((self.current_func, called_func, call_line))
            elif isinstance(node.func, ast.Attribute):
                try:
                    value = ast.unparse(node.func.value)
                    attr = node.func.attr
                    # 处理cls.method()形式的调用（类方法）
                    if value == 'cls' and self.current_class:
                        called_func = f"{self.current_class}.{attr}"
                        call_line = node.lineno
                        self.calls.append((self.current_func, called_func, call_line))
                    
                    # 处理模块.函数形式和类对象.方法形式的调用
                    if value in self.classes:  # value是类名
                        called_func = f"{value}.{attr}"
                        call_line = node.lineno
                        self.calls.append((self.current_func, called_func, call_line))
                    # 处理self.method()形式的调用
                    elif value == 'self' and self.current_class:
                        # 检查是否是继承的方法
                        if attr in self.classes[self.current_class]['inherited_methods']:
                            for base in self.classes[self.current_class]['bases']:
                                if base in self.classes and attr in self.classes[base]['methods']:
                                    called_func = f"{base}.{attr}"
                                    call_line = node.lineno
                                    self.calls.append((self.current_func, called_func, call_line))
                                    break
                        else:
                            called_func = f"{self.current_class}.{attr}"
                            call_line = node.lineno
                            self.calls.append((self.current_func, called_func, call_line))
                    # 如果是相对导入的模块函数调用
                    elif value.startswith('.'):
                        called_func = f"{value}.{attr}"
                        call_line = node.lineno
                        self.calls.append((self.current_func, called_func, call_line))
                except Exception as e:
                    # 处理解析错误
                    pass
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
    for file_path, _ in set(functions.values()):
        file_nodes.add(file_path)
        safe_path = file_path.replace('\\', '\\\\')
        cypher_commands.append(
            f"MERGE (f:PythonFile {{path: '{safe_path}'}});\n"  # CREATE -> MERGE
        )
    
    # 创建函数节点并关联到文件
    for func, (file_path, line_number) in functions.items():
        file_name = os.path.basename(file_path)
        safe_path = file_path.replace('\\', '\\\\')
        cypher_commands.append(
            f"CREATE (fn:PythonFunction {{name: '{func}', line_number: {line_number}, file_name: '{file_name}'}});\n"  # CREATE -> MERGE
            f"MATCH (f:PythonFile {{path: '{safe_path}'}}), (fn:PythonFunction {{name: '{func}'}}) "
            f"CREATE (fn)-[:DEFINED_IN {{line_number: {line_number}}}]->(f);\n"  # CREATE -> MERGE
        )
    
    # 创建调用关系
    for caller, callee, line in calls:
        cypher_commands.append(
            f"MATCH (a:PythonFunction {{name: '{caller}'}}), (b:PythonFunction {{name: '{callee}'}}) "
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
    project_path = "D:\\workspace\\OpenManus-main"  # 修改为你的Python项目路径
    cypher_commands = analyze_python_project(project_path)
    
    # 将Cypher语句保存到文件
    output_file = "D:\\workspace\\OpenManus-main\\output.cypher"
    with open(output_file, 'w', encoding='utf-8') as f:
        for command in cypher_commands:
            f.write(command)
    
    print(f"Cypher语句已保存到 {output_file}")