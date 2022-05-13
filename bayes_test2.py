from bayes import BayesGraph, BayesNode

# Test load of earthquake bif file
# https://www.bnlearn.com/bnrepository/discrete-small.html#earthquake

bg = BayesGraph()
with open("earthquake.bif", "r") as f:
    bif = f.read()
bg.load_bif(bif)
print(bg)

obs_node = bg.get_node("MaryCalls")
obs_node.fix_value("True")

node_of_interest = bg.get_node("Burglary")
val_of_interest = "True"
posterior_pr, num_hypo, num_valid = bg.get_posterior(node_of_interest, val_of_interest, sims_count=10000)

print(f"{posterior_pr}, {num_hypo}/{num_valid}")
