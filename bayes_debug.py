from bayes import BayesGraph, BayesNode

# Test load of earthquake bif file
# https://www.bnlearn.com/bnrepository/discrete-small.html#earthquake

bg = BayesGraph()
with open("infer.bif", "r") as f:
    bif = f.read()
bg.load_bif(bif)
print(bg)

obs_node = bg.get_node("detectSoundOfGlass")
obs_node.fix_value("1")
obs_node = bg.get_node("detectVisibleKnife")
obs_node.fix_value("1")
obs_node = bg.get_node("detectAlarmingTweet")
obs_node.fix_value("1")

node_of_interest = bg.get_node("attacker")
val_of_interest = "1"
posterior_pr, num_hypo, num_valid = bg.get_posterior(node_of_interest, val_of_interest, sims_count=10000)

print(f"{posterior_pr}, {num_hypo}/{num_valid}")

with open("double_encoded.bif", "w") as f:
    f.write(bg.to_bif())

with open("double_encoded.dump", "w") as f:
    f.write(str(bg._dump()))