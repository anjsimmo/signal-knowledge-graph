from bayes import BayesGraph, BayesNode

# http://www.cs.man.ac.uk/~gbrown/bayes_nets
# burgulary/alarm example

bg = BayesGraph()

eq = BayesNode("earthquake")
eq.add_output_value(1)
eq.add_output_value(0)
eq.add_row([],[0.002, 0.998])

b = BayesNode("burgulary")
b.add_output_value(1)
b.add_output_value(0)
b.add_row([],[0.001, 0.999])

a = BayesNode("alarm")
a.add_condition(eq)
a.add_condition(b)
a.add_output_value(1)
a.add_output_value(0)
a.add_row([1,1],[0.95,0.05])
a.add_row([1,0],[0.94,0.06])
a.add_row([0,1],[0.29,0.71])
a.add_row([0,0],[0.001,0.999])

j = BayesNode("johncalls")
j.add_condition(a)
j.add_output_value(1)
j.add_output_value(0)
j.add_row([1],[0.9,0.1])
j.add_row([0],[0.05,0.95])

m = BayesNode("marycalls")
m.add_condition(a)
m.add_output_value(1)
m.add_output_value(0)
m.add_row([1],[0.7,0.3])
m.add_row([0],[0.01,0.99])

bg.add_node(eq)
bg.add_node(b)
bg.add_node(a)
bg.add_node(j)
bg.add_node(m)

print(bg)