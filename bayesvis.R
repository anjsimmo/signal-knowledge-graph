library(bnlearn)

g = read.bif("infer.bif")
pdf("infer_graph.pdf")
graphviz.plot(g, layout = "dot", shape = "ellipse")
dev.off()
cpquery(g, event = (attacker == "1"), evidence = (det_smartlavplusMicrophone_soundOfGlass == "1"), n = 1000000)
