import { useState, useEffect, useContext } from 'preact/hooks'
import { cloneDeep } from "lodash"

import Graph from "graphology";
import { GraphContext } from './context'


type LoadGraphProps = {
    jsonDependencies: Map<string, Array<string>>
}


// function to Parse the JSON file to graphology graph
function parseJSONtoGraph(json: Map<string, Array<string>>) : Graph {
    console.log('parse graph')
    const graph = new Graph();
    // iterate over key and value of json file
    json.forEach((value, key) => {
        graph.mergeNode(key, { id: key, x: Math.random(), y: Math.random(), size: 5 });
        // iterate over value of key
        for (const dependency of value) {
            // add node to graph
            graph.mergeNode(dependency, { id: dependency });
            // add edge to graph
            graph.addEdge(key, dependency);
            graph.updateNodeAttribute(key, 'size', n => n + 1);
        }
        }
    )
    return graph;
}

export function LoadGraph({ jsonDependencies }: LoadGraphProps) {
    const { graph, graphVersion, saveGraph, setData } = useContext(GraphContext);

    useEffect(() => {
        // parse json file to graphology graph
        const graph = parseJSONtoGraph(jsonDependencies);
        // set graph state
        saveGraph(graph);
    }, []);
    useEffect(() => {
        // set data state

        if (!graph) {
            return
        }
        const nodes = graph.filterNodes((node, attributes) => {
            if (!attributes.hidden) {
                return true
            } else {
                return false
            }
        }).map(node =>
            graph.getNodeAttributes(node)
        )
        const links = graph.mapEdges((edge, attributes, source, target) => {
            if (!graph.getNodeAttribute(source, 'hidden') && !graph.getNodeAttribute(target, 'hidden')) {
                return {
                    source: source,
                    target: target,
                    id: edge,
                    ...attributes,
                }
            }

        }
        ).filter(link => link !== undefined)
        setData({ nodes, links })
    }, [graphVersion]);

    return null;
}

export function GraphContainer({ children }) {

    // graph state
    const [graph, setGraph] = useState<Graph>();
    const [data, setData] = useState({ nodes: [], links: [] });
    const [graphVersion, setGraphVersion] = useState(0);

    function saveGraph(graph: Graph) {
        setGraphVersion(Math.random());
        setGraph(graph);
    };

    return (
        <GraphContext.Provider value={{
            graph, saveGraph, data, setData, graphVersion, setGraphVersion
        }}>
            {children}
        </GraphContext.Provider>
    )
}




