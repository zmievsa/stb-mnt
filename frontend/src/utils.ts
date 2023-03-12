export function selectNode(node: string | null, graph) {
    if (!node) {
        return null;
    }
    resetGraph(graph)
    graph.forEachEdge(node, (edge, attributes, source, target) => {
        if (source === node) {
            graph.setEdgeAttribute(edge, 'color', 'red');
            graph.setEdgeAttribute(edge, 'type', 'my-fast');
        }
        else {
            graph.setEdgeAttribute(edge, 'color', 'blue');
        }
        console.log(attributes);
        graph.setEdgeAttribute(edge, 'size', 3);
        graph.setNodeAttribute(target, 'highlighted', true)
        graph.setNodeAttribute(target, 'color', 'blue')

        graph.setNodeAttribute(source, 'highlighted', true)
        graph.setNodeAttribute(source, 'color', 'pink')
    })

}

export function resetGraph(graph) {
    graph.forEachNode((node) => {
        graph.removeNodeAttribute(node, 'highlighted');
        graph.setNodeAttribute(node, 'color', 'black');
        graph.setNodeAttribute(node, 'highlighted', false);
    }
    );
    graph.forEachEdge((edge) => {
        graph.removeEdgeAttribute(edge, 'highlighted');
        graph.setEdgeAttribute(edge, 'color', '#ccc');
        graph.setEdgeAttribute(edge, 'highlighted', false);
        graph.setEdgeAttribute(edge, 'size', 2);
    }
    );

}
