import random
import re


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
    return str(name) # ensure name is string


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
    
    def get_posterior(self, node, node_output_val, sims_count=1000, min_sample = 1):
        assert node_output_val in node.get_output_vals() # check that it is actually possible to output value
        
        # Inefficient, but demonstrates concept
        sims = []
        valid_sims = []
        valid_sims_consistent_hypo = []
        for i in range(sims_count):
            sim = self._single_sim()
            sims.append(sim)
            if self._check_sim_consistent_obs(sim):
                valid_sims.append(sim)
                if self._check_sim_consistent_hypo(sim, node, node_output_val):
                    valid_sims_consistent_hypo.append(sim)
        
        if len(valid_sims) < min_sample:
            # insufficient samples to make an estimate
            pr = float("nan")
        else:
            pr = len(valid_sims_consistent_hypo) / len(valid_sims)

        num_hypo = len(valid_sims_consistent_hypo)
        num_valid = len(valid_sims)
        return pr, num_hypo, num_valid
        
    def _single_sim(self):
        # node -> val
        sampled_values = {}
        
        # Sample nodes conditionally
        while True:
            change = False
            for n in self.nodes:
                # Loop until we find an unsimulated node with all inputs computed (inefficient!)
                if n in sampled_values:
                    continue
                conditions_met = True
                for c in n.condition_nodes:
                    if not c in sampled_values:
                        conditions_met = False
                if not conditions_met:
                    continue
                conditions = tuple(sampled_values[cn] for cn in n.condition_nodes)
                weights = n.condition_to_prs[conditions]
                val = random.choices(n.output_vals, weights)[0]
                sampled_values[n] = val
                change = True
            if not change:
                # Ensure all nodes were sampled
                # (this could fail if there are disconnected nodes in graph)
                for n in self.nodes:
                    assert n in sampled_values
                break
        
        return sampled_values

    def _check_sim_consistent_obs(self, sampled_values):
        # Return true if simulation is consistent with fixed observation nodes
        # Loop over fixed nodes and check output is consistent.
        for node, val in sampled_values.items():
            if node.fixed_value is not None:
                if node.fixed_value != val:
                    return False
        return True

    def _check_sim_consistent_hypo(self, sampled_values, node_hypo, node_output_val):
        # Return true if simulation is consistent with hypothesised node_output_val
        assert node_hypo in sampled_values
        return sampled_values[node_hypo] == node_output_val
    
    def to_bif(self):
        # Write bif output (old style) reverse enginered from bnlearn examples at https://www.bnlearn.com/bnrepository/
        s = """network unknown {
}"""
        for n in self.nodes:
            s += f"""
variable {n.name} {{
  type discrete [ {len(n.output_vals)} ] {{ {", ".join(str(x) for x in n.output_vals)} }}
}}"""
        for n in self.nodes:
            if not n.condition_nodes:
                s += f"""
probability ( {n.name} ) {{
  table {", ".join(str(x) for x in n.rows[0][1])};
}}"""
            else:
                s += f"""
probability ( {n.name} | {", ".join(n.condition_node_names)} ) """ + "{"
                for r in n.rows:
                    s += f"""
  ({", ".join(str(x) for x in r[0])}) {", ".join(str(x) for x in r[1])};"""
                s += """
}"""
        s += "\n"
        return s
        
    def use_shortnames(self):
        # shortname -> count of nodes with this name
        shortname_count = {}
        for n in self.nodes:
            if n.shortname in shortname_count:
                shortname_count[n.shortname] += 1
                n.name = f"{n.shortname}{shortname_count[n.shortname]}"
            else:
                shortname_count[n.shortname] = 1
                n.name = n.shortname

        for n in self.nodes:
            n.condition_node_names = [cn.name for cn in n.condition_nodes]
    
    def load_bif(self, bif):
        # nodes
        ms = re.finditer(r"^variable (?P<name>\w+) {\n  type discrete \[ \d* \] { (?P<varlist>[\w., ]*) }", bif, re.MULTILINE)
        for m in ms:
            d = m.groupdict()
            n = BayesNode(d["name"])
            for var in d["varlist"].split(", "):
                n.add_output_value(var)
            self.add_node(n)

        # probability tables
        ms = re.finditer(r"^probability \( (?P<name>\w+) \) {\n  table (?P<row>[\w., ]*);", bif, re.MULTILINE)
        for m in ms:
            d = m.groupdict()
            n = self.get_node(d["name"])
            row_vals = d["row"].split(", ")
            n.add_row([], [float(f) for f in row_vals])

        # conditional probability tables
        ms = re.finditer(r"^probability \( (?P<name>\w+) \| (?P<conditionlist>[\w, ]+) \) {\n(?P<rows>(.*;\n)*)}$", bif, re.MULTILINE)
        for m in ms:
            d = m.groupdict()
            n = self.get_node(d["name"])
            for condition_name in d["conditionlist"].split(", "):
                cn = self.get_node(condition_name)
                n.add_condition(cn)
            rows = d["rows"].split("\n")
            for row in rows:
                if row == "":
                    continue
                d = re.search(r"^\s*\((?P<conditions>[\w\., ]+)\) (?P<vals>[\w\., ]+);", row).groupdict()
                conditions = d["conditions"].split(", ")
                vals = d["vals"].split(", ")
                n.add_row(conditions, [float(f) for f in vals])

    def _dump(self):
        # dump internal values (for debugging purposes)
        return [[n._dump() for n in self.nodes], [(k,v.name) for k,v in self.node_name_index.items()]]


# conditional probability table
# Designed to be similar to tool at http://www.cs.man.ac.uk/~gbrown/bayes_nets
class BayesNode:
    def __init__(self, name=None):
        self.name = default_name(name)
        self.condition_nodes = []
        self.condition_node_names = []
        self.output_vals = []
        self.rows = []
        self.fixed_value = None
        # condition_vals -> output_value_prs
        self.condition_to_prs = {}
        self.shortname = self.name
    
    def add_condition(self, condition_node):
        self.condition_nodes.append(condition_node)
        self.condition_node_names.append(condition_node.name)
    
    def add_output_value(self, name=None):
        name = default_name(name)
        self.output_vals.append(name)
    
    def add_row(self, condition_vals, output_value_prs):
        output_value_prs = [float(x) for x in output_value_prs] # ensure prs are floats
        condition_vals = [str(x) for x in condition_vals]
        row = (condition_vals, output_value_prs)
        self.rows.append(row)
        assert tuple(condition_vals) not in self.condition_to_prs # ensure no dup rows
        self.condition_to_prs[tuple(condition_vals)] = output_value_prs
    
    def fix_value(self, output_value):
        # Fixed observation value
        output_value = str(output_value)
        assert output_value in self.output_vals
        self.fixed_value = output_value
    
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
        
        if self.fixed_value:
            s += f"fixed value: {self.fixed_value}" + "\n" 

        return s
    
    def _dump(self):
        # dump internal values (for debugging purposes)
        return [self.name, [cn.name for cn in self.condition_nodes], self.condition_node_names, self.output_vals, self.rows, self.fixed_value, self.condition_to_prs, self.shortname]
