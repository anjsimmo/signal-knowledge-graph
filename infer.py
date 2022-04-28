import math
import itertools
from bayes import BayesGraph, BayesNode

from rdflib import Graph, Namespace, RDF, SKOS
g = Graph()
g.parse('signal.shapes.ttl', format='ttl')

import pprint
for stmt in g:
    pprint.pprint(stmt)

# V1
# Simulate all possible universes
# Filter to those consistent with observations
# calculate posterior pr


# V2
# Generate bayesian graph
# SNR vs Pr
# (high, med, low)
# - would still require heuristic!

# V3
# Assume discrete output
# Gen bayesian graph (with some parts as functions)
# Brute force to solve


signal = Namespace("http://a2i2.deakin.edu.au/signal#")

causal_graph = BayesGraph()

def get_name(uriref):
    return uriref.split('#')[-1]

def pr_actor(causal_graph):
    persons = list(g.subjects(RDF.type, signal.Person))
    nodes = []
    for person in persons:
        pr_exists = float(g.value(person, signal.pr_exists).value)
        n = BayesNode(get_name(person))
        n.add_output_value(1)
        n.add_output_value(0)
        n.add_row([],[pr_exists,1-pr_exists])
        nodes.append(n)
    return nodes

actor_nodes = pr_actor(causal_graph)
print(actor_nodes)
for n in actor_nodes:
    causal_graph.add_node(n)

def pr_action_given_actor(causal_graph):
    nodes = []
    for actor in g.subjects(RDF.type, signal.Person):
        behaviours = list(g.subjects(signal.actor, actor))
        for behaviour in behaviours:
            # Should be of type Behaviour
            assert len(list(g.triples((behaviour, RDF.type, signal.Behaviour)))) >= 1
            pr = float(g.value(behaviour, signal.pr).value)
            actions = g.objects(behaviour, signal.produces)
            acts_on = g.objects(behaviour, signal.actsOn)
            locations = [g.value(ao, signal.loc) for ao in acts_on]
            #results += [(action, pr, actor, loc) for action in actions for loc in locations]
            for action in actions:
                for loc in locations:
                     # action, pr, actor, loc
                     n = BayesNode(get_name(actor) + "_" + get_name(action) + "_" + get_name(loc))
                     actor_node = causal_graph.get_node(get_name(actor))
                     n.actor = actor
                     n.action = action
                     n.source_loc = loc
                     n.add_condition(actor_node)
                     n.add_output_value(1)
                     n.add_output_value(0)
                     n.add_row([0],[0,1])
                     n.add_row([1],[pr,1-pr])
                     nodes.append(n)
    return nodes

action_nodes = pr_action_given_actor(causal_graph)
print(action_nodes)
for n in action_nodes:
    causal_graph.add_node(n)

def pr_signal_given_action(causal_graph):
    emissions = g.subjects(RDF.type, signal.Emission)
    nodes = []
    for emission in emissions:
        signals = g.objects(emission, signal.creates)
        actions = g.objects(emission, signal.emissionAction)
        #results += [(sig, action) for action in actions for sig in signals]
        for sig in signals:
            for action in actions:
                for action_node in causal_graph.get_nodes("_" + get_name(action) + "_"):
                    n = BayesNode(action_node.name + "_signal_" + get_name(sig))
                    n.actor = action_node.actor
                    n.action = action_node.action
                    n.source_loc = action_node.source_loc
                    n.sig = sig
                    n.add_condition(action_node)
                    n.add_output_value(1)
                    n.add_output_value(0)
                    n.add_row([0],[0,1])
                    n.add_row([1],[1,0])
                    nodes.append(n)
    return nodes

signal_nodes = pr_signal_given_action(causal_graph)
print(signal_nodes)
for n in signal_nodes:
    causal_graph.add_node(n)

def inverse_square_fall_off(dist):
    # TODO: Convert to decibels?
    if dist == 0:
        return float('inf')

    return 1 / dist**2

def dist(loca, locb):
    x1 = float(g.value(loca, signal.locx).value)
    y1 = float(g.value(loca, signal.locy).value)
    x2 = float(g.value(locb, signal.locx).value)
    y2 = float(g.value(locb, signal.locy).value)
    # TODO: perform geodesic calculation (or just use x, y coordinate system instead)
    return math.sqrt((x2-x1)**2 + (y2-y1)**2)

def pr_signal_strength_given_signal(causal_graph):
    # TODO: Get action locations!!!!
    sensors = list(g.subjects(RDF.type, signal.Sensor))
    
    sensor_locs = []
    for sensor in sensors:
        location = g.value(sensor, signal.loc)
        sensor_locs.append((sensor, location))
    
    signal_nodes = causal_graph.get_nodes("_signal_")
    
    nodes = []
    for sensor, sensor_loc in sensor_locs:
        for signal_node in signal_nodes:
            actor = signal_node.actor
            source_loc = signal_node.source_loc
            
            d = dist(source_loc, sensor_loc)
            reduction_factor = inverse_square_fall_off(d)
            
            n = BayesNode(signal_node.name + "_" + get_name(sensor) + "_strength")
            n.actor = signal_node.actor
            n.action = signal_node.action
            n.source_loc = signal_node.source_loc
            n.sig = signal_node.sig
            n.sensor_loc = sensor_loc
            n.sensor = sensor
            n.strength = reduction_factor
            n.add_condition(signal_node)
            n.add_output_value(reduction_factor)
            n.add_output_value(0)
            n.add_row([0],[0,1])
            n.add_row([reduction_factor],[1,0])
            nodes.append(n)
    return nodes

strength_nodes = pr_signal_strength_given_signal(causal_graph)
print(strength_nodes)
for n in strength_nodes:
    causal_graph.add_node(n)

# https://stackoverflow.com/questions/3985619/how-to-calculate-a-logistic-sigmoid-function-in-python
def sigmoid(x):
    return 1 / (1 + math.exp(-x))

def pr_det_given_signal_strength_helper(sig_strength, ref_signal, sensitivity, specificity):
    # TODO: depends on whether using power, or decibel scale
    # assert sensitivity >= 0.5
    # assert specificity >= 0.5
    # TODO: plot this curve to make sure it looks right
    tpr = sensitivity
    fpr = 1 - specificity
    # Full signal => TPR
    # No signal => FPR
    adjusted_sensitivity = tpr - (tpr - fpr) * (1 - sigmoid(sig_strength/ref_signal)) * 2
    return adjusted_sensitivity


def pr_det_given_signal_strength(causal_graph):
    sensors = list(g.subjects(RDF.type, signal.Sensor))
    
    sensor_obs = []
    for sensor in sensors:
        model = g.value(sensor, signal.model)
        observed_signals = g.objects(model, signal.input)
        sensitivity = float(g.value(model, signal.sensitivity).value)
        specificity = float(g.value(model, signal.specificity).value)
        sensor_obs += [(sensor, obssig, sensitivity, specificity) for obssig in observed_signals]

    nodes = []
    for sensor, observed_signal, sensitivity, specificity in sensor_obs:
        #print("DEBUG: " + "_signal_" + get_name(observed_signal) + "_" + get_name(sensor) + "_strength")
        
        # TODO: Recurse
        broader_signals = g.subjects(SKOS.broader, observed_signal)
        strength_nodes = []
        for sig in broader_signals:
            strength_nodes += causal_graph.get_nodes("_signal_" + get_name(sig) + "_" + get_name(sensor) + "_strength")
        
        n = BayesNode("det_" + get_name(sensor) + "_" + get_name(observed_signal))
        for sn in strength_nodes:
            n.add_condition(sn)
        
        n.add_output_value(1)
        n.add_output_value(0)
        
        # [(0, 0, 0, 0, 0), (0, 0, 0, 0, 1), ...]
        combos = itertools.product([0,1], repeat=len(strength_nodes))
        for combo in combos:
            row_condition = list(combo)

            strengths = []
            for i, c in enumerate(combo):
                if c == 0:
                    continue
                strengths.append(strength_nodes[i].strength)
            
            max_strenth = max([0] + strengths)
            pr_det = pr_det_given_signal_strength_helper(max_strenth, 1, sensitivity, specificity)
            
            n.add_row(row_condition,[pr_det, 1 - pr_det])
        
        nodes.append(n)

    return nodes


det_nodes = pr_det_given_signal_strength(causal_graph)
print(det_nodes)
for n in det_nodes:
    causal_graph.add_node(n)

def gen_causal_graph():
    pass
    # causal_graph = BayesGraph()
    # 
    # a = pr_actor()
    # act = pr_action_given_actor()
    # sig = pr_signal_given_action()
    # strength = pr_signal_given_action()
    # det = pr_det_given_signal_strength()
    # 
    # causal_graph.add_node(a)
    # causal_graph.add_node(act)
    # causal_graph.add_node(sig)
    # causal_graph.add_node(strength)
    # causal_graph.add_node(det)
    # 
    # return causal_graph


def infer_actor_pr(actor, causal_graph, obs):
    pass


def monitor_step(obs):
    alarm = False
    def raise_alarm():
        alarm = True
        
    causal_graph = gen_causal_graph()
    posterior_cause = infer_actor_pr(causal_graph, obs)
    if posterior_cause.get_probability("attacker") > 0.5:
        raise_alarm()
    return alarm

