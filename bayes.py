def id_gen():
    id = 0
    while True:
        yield id
        id += 1

ids = id_gen()

def name_gen():
    return f"id{ids.__next__()}"

def default_name(name):
    if name == None:
        return name_gen()
    return name

class BayesGraph:
    def __init__(self):
        self.nodes = []
        # name -> node
        self.node_name_index = {}

    def add_node(self, node):
        self.nodes.append(node)
        self.node_name_index[node.name] = node
    
    def get_node(self, node_name):
        return self.node_name_index[node_name]

    def get_nodes(self, node_partial_name):
        return list(filter(lambda n: node_partial_name in n.name, self.nodes))
    
    def __repr__(self):
        s = ""
        for n in self.nodes:
            s += str(n) + "\n"
        return s

# conditional probability table
# Designed to be similar to tool at http://www.cs.man.ac.uk/~gbrown/bayes_nets
class BayesNode:
    def __init__(self, name=None):
        self.name = default_name(name)
        self.condition_nodes = []
        self.condition_node_names = []
        self.output_vals = []
        self.rows = []
    
    def add_condition(self, condition_node):
        self.condition_nodes.append(condition_node)
        self.condition_node_names.append(condition_node.name)
    
    def add_output_value(self, name=None):
        name = default_name(name)
        self.output_vals.append(name)
    
    def add_row(self, condition_vals, output_value_prs):
        row = (condition_vals, output_value_prs)
        self.rows.append(row)
    
    def get_output_vals(self):
        return self.output_vals
    
    def __repr__(self):
        s = f"==={self.name}===\n"
        header = []
        for cn in self.condition_node_names:
            header.append(cn)
        for ov in self.output_vals:
            header.append("P(" + self.name + "=" + str(ov) + ")")
        s += ",".join(header) + "\n"
        
        for condition_vals, output_value_prs in self.rows:
            row = []
            row += condition_vals
            row += output_value_prs
            s += ",".join([str(x) for x in row]) + "\n"

        return s
