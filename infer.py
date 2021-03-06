import math
import itertools
from collections import namedtuple
from rdflib import Graph, Namespace, RDF, SKOS
from rdflib.exceptions import UniquenessError
from bayes import BayesGraph, BayesNode


SIGNAL_KG_FILE = 'signal.ttl'

g = Graph()
g.parse(SIGNAL_KG_FILE, format='ttl')
signal = Namespace("http://a2i2.deakin.edu.au/signal#")
Posterior = namedtuple("Posterior", ["pr", "num_hypo", "num_valid"])


def _capitalise(s):
    # capitalise just the first letter, leave rest as is
    return s[0:1].upper() + s[1:]


def get_name(uriref):
    return uriref.split('#')[-1]


def pr_actor(causal_graph):
    nodes = []

    for person in g.subjects(RDF.type, signal.Person):
        n = BayesNode(get_name(person))
        n.add_output_value(1)
        n.add_output_value(0)
        pr_exists = float(g.value(person, signal.pr_exists))
        n.add_row([],[pr_exists,1-pr_exists])
        nodes.append(n)

    for trigger in g.subjects(RDF.type, signal.Trigger):
        n = BayesNode(get_name(trigger))
        n.add_output_value(1)
        n.add_output_value(0)
        # Will create the probability table later (once rest of graph is created)
        assert len(list(g.objects(trigger, signal.triggerSensor))) > 0
        assert len(list(g.objects(trigger, signal.triggerSignal))) > 0
        nodes.append(n)

    return nodes


def link_triggers(causal_graph):
    nodes = []
    for actor in g.subjects(RDF.type, signal.Trigger):
        actor_node = causal_graph.get_node(get_name(actor))
        trigger_sensors = list(g.objects(actor, signal.triggerSensor))
        trigger_signals = list(g.objects(actor, signal.triggerSignal))
        assert trigger_sensors
        assert trigger_signals
        for sensor in trigger_sensors:
            for observed_signal in trigger_signals:
                sensor_node = causal_graph.get_node("det_" + get_name(sensor) + "_" + get_name(observed_signal))
                actor_node.add_condition(sensor_node)
        # Implement OR condition
        # [(0, 0, 0, 0, 0), (0, 0, 0, 0, 1), ...]
        combos = itertools.product([0,1], repeat=len(actor_node.condition_nodes))
        for combo in combos:
            if 1 in combo:
                # 1 or more 1s => true
                actor_node.add_row(combo,[1,0])
            else:
                # all 0s => false
                actor_node.add_row(combo,[0,1])


def pr_action_given_actor(causal_graph):
    nodes = []
    for actor in (list(g.subjects(RDF.type, signal.Person)) + list(g.subjects(RDF.type, signal.Trigger))):
        behaviours = list(g.subjects(signal.actor, actor))
        for behaviour in behaviours:
            # Should be of type Behaviour
            assert len(list(g.triples((behaviour, RDF.type, signal.Behaviour)))) >= 1
            pr = float(g.value(behaviour, signal.pr).value)
            actions = g.objects(behaviour, signal.produces)
            acts_on = g.objects(behaviour, signal.actsOn)
            locations = [g.value(ao, signal.loc) for ao in acts_on]
            for action in actions:
                for loc in locations:
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
                     n.shortname = get_name(action)
                     nodes.append(n)
    return nodes


def pr_signal_given_action(causal_graph):
    emissions = g.subjects(RDF.type, signal.Emission)
    nodes = []
    for emission in emissions:
        signals = list(g.objects(emission, signal.creates))
        actions = list(g.objects(emission, signal.emissionAction))
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
                    n.shortname = get_name(sig)
                    nodes.append(n)
    return nodes


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
    sensors = list(g.subjects(RDF.type, signal.Sensor))
    
    sensor_locs = []
    for sensor in sensors:
        location = g.value(sensor, signal.loc)
        sensor_locs.append((sensor, location))
    
    signal_nodes = causal_graph.get_nodes("_signal_")
    
    nodes = []
    for sensor, sensor_loc in sensor_locs:
        sensor_model = g.value(sensor, signal.model)
        sensor_observed_signals = set(g.objects(sensor_model, signal.input))
        sensor_signals = set(b for obs_sig in sensor_observed_signals for b in get_narrower_signals(obs_sig))
        sensor_signals |= set(b for obs_sig in sensor_observed_signals for b in get_broader_signals(obs_sig))
        sensor_signals |= sensor_observed_signals
        
        for signal_node in signal_nodes:
            if not signal_node.sig in sensor_signals:
                # sensor can't detect this kind of signal, so ignore
                continue

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
            n.add_row([1],[1,0])
            n.shortname = get_name(n.sig) + "Strength"
            nodes.append(n)
    return nodes


# https://stackoverflow.com/questions/3985619/how-to-calculate-a-logistic-sigmoid-function-in-python
def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def get_narrower_signals(observed_signal):
    # TODO: Recurse
    narrower_signals = g.subjects(SKOS.broader, observed_signal)
    return narrower_signals


def get_broader_signals(observed_signal):
    # TODO: Recurse
    broader_signals = g.objects(SKOS.broader, observed_signal)
    return broader_signals


def pr_det_given_signal_strength_helper(sig_strength, ref_signal, sensitivity, specificity):
    # TODO: depends on whether using power, or decibel scale
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
        narrower_signals = [observed_signal] + list(get_narrower_signals(observed_signal))
        strength_nodes = []
        for sig in narrower_signals:
            strength_nodes += causal_graph.get_nodes("_signal_" + get_name(sig) + "_" + get_name(sensor) + "_strength")
        
        n = BayesNode("det_" + get_name(sensor) + "_" + get_name(observed_signal))
        for sn in strength_nodes:
            n.add_condition(sn)
        
        n.add_output_value(1)
        n.add_output_value(0)
        
        strength_combos = []

        for sn in strength_nodes:
            strength_combos.append(sn.output_vals)

        for combo in itertools.product(*strength_combos):
            row_condition = list(combo)
            max_strenth = max([0] + [float(x) for x in row_condition])
            pr_det = pr_det_given_signal_strength_helper(max_strenth, 1, sensitivity, specificity)
            n.add_row(row_condition,[pr_det, 1 - pr_det])

        n.shortname = "detect" + _capitalise(get_name(observed_signal))
        nodes.append(n)

    return nodes


def fix_observation_values(causal_graph):
    observations = list(g.subjects(RDF.type, signal.Observation))

    for obs in observations:
        sensor = g.value(obs, signal.observedBy)
        sig = g.value(obs, signal.observedSignal)
        val = g.value(obs, signal.value)
        
        n = causal_graph.get_node("det_" + get_name(sensor) + "_" + get_name(sig))
        n.fix_value(int(val))


def gen_causal_graph():
    causal_graph = BayesGraph()

    actor_nodes = pr_actor(causal_graph)
    for n in actor_nodes:
        causal_graph.add_node(n)

    action_nodes = pr_action_given_actor(causal_graph)
    for n in action_nodes:
        causal_graph.add_node(n)

    signal_nodes = pr_signal_given_action(causal_graph)
    for n in signal_nodes:
        causal_graph.add_node(n)

    strength_nodes = pr_signal_strength_given_signal(causal_graph)
    for n in strength_nodes:
        causal_graph.add_node(n)

    det_nodes = pr_det_given_signal_strength(causal_graph)
    for n in det_nodes:
        causal_graph.add_node(n)
    
    link_triggers(causal_graph)

    return causal_graph


class Alarm:
    def __init__(self):
        self.alarm = False
        self.msg = ""
    
    def warn(self, pr, msg):
        self.msg = msg

    def alert(self):
        self.alarm = True
    
    def __repr__(self):
        return f"alarm={self.alarm} - {self.msg}"


def infer_actor_pr(causal_graph, actor_name, actor_val):
    n = causal_graph.get_node(actor_name)
    posterior_pr, num_hypo, num_valid = causal_graph.get_posterior(n, actor_val, sims_count=10000)
    return Posterior(pr = posterior_pr, num_hypo = num_hypo, num_valid = num_valid)


def monitor_step():
    alarm = Alarm()

    causal_graph = gen_causal_graph()
    fix_observation_values(causal_graph)

    posterior_cause = infer_actor_pr(causal_graph, "attacker", "1")
    msg = f"Attacker in {posterior_cause.num_hypo}/{posterior_cause.num_valid} sims => Pr(attacker) = {posterior_cause.pr}"
    alarm.warn(posterior_cause.pr, msg)
    if posterior_cause.pr > 0.5:
        alarm.alert()
    return alarm, causal_graph


if __name__ == "__main__":
    alarm, causal_graph = monitor_step()
    causal_graph.use_shortnames()
    print(causal_graph)
    
    print(f"{alarm}")
    
    with open("infer.bif", "w") as f:
        f.write(causal_graph.to_bif())

    with open("infer.dump", "w") as f:
        f.write(str(causal_graph._dump()))