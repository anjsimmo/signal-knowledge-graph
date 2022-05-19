from bayes import BayesGraph, BayesNode


# burgulary/alarm example
# http://www.cs.man.ac.uk/~gbrown/bayes_nets (wrong values for burgulary)
# https://www.bnlearn.com/bnrepository/discrete-small.html#earthquake (values used for this example)

bg = BayesGraph()

b = BayesNode("Burglary")
b.add_output_value(1)
b.add_output_value(0)
b.add_row([],[0.01, 0.99])

eq = BayesNode("Earthquake")
eq.add_output_value(1)
eq.add_output_value(0)
eq.add_row([],[0.02, 0.98])

a = BayesNode("Alarm")
a.add_condition(b)
a.add_condition(eq)
a.add_output_value(1)
a.add_output_value(0)
a.add_row([1,1],[0.95,0.05])
a.add_row([0,1],[0.29,0.71])
a.add_row([1,0],[0.94,0.06])
a.add_row([0,0],[0.001,0.999])

j = BayesNode("JohnCalls")
j.add_condition(a)
j.add_output_value(1)
j.add_output_value(0)
j.add_row([1],[0.9,0.1])
j.add_row([0],[0.05,0.95])

m = BayesNode("MaryCalls")
m.add_condition(a)
m.add_output_value(1)
m.add_output_value(0)
m.add_row([1],[0.7,0.3])
m.add_row([0],[0.01,0.99])

bg.add_node(b)
bg.add_node(eq)
bg.add_node(a)
bg.add_node(j)
bg.add_node(m)

print(bg)

# condtional upon observation
obs_node = bg.get_node("MaryCalls")
obs_node.fix_value(1)

node_of_interest = bg.get_node("Burglary")
val_of_interest = "1"
posterior_pr, num_hypo, num_valid = bg.get_posterior(node_of_interest, val_of_interest, sims_count=10000)

print(f"{posterior_pr}, {num_hypo}/{num_valid}")

with open("test.bif", "w") as f:
    f.write(bg.to_bif())
