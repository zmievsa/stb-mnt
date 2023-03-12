import { useRef, useContext, useState, useCallback, useEffect } from 'preact/hooks'
import { ForceGraph2D } from 'react-force-graph'
import { GraphContext, GraphData } from './context'
import Graph from "graphology";

const NODE_R = 5;

const highlightNeighbors = (graph, node, setHighlitedNode) => {
    if (node === null) {
        // resetGraph(graph)
        // TODO
        setHighlitedNode(null)
        return
    }
    setHighlitedNode(node.id)
}

export const GraphRender = () => {
    const fgRef = useRef();

    const { graph, data, graphVersion } = useContext(GraphContext)

    const [highlightNodes, setHighlightNodes] = useState(new Set());
    const [highlightLinks, setHighlightLinks] = useState(new Set());
    const [hoverNode, setHoverNode] = useState(null);

    // log graph
    useEffect(() => {
        console.log(fgRef.current.d3Force('link').strength(0.2))
        console.log(fgRef.current.d3Force('charge').strength(-100))
        console.log(fgRef.current.d3Force('center').strength(1.8))
    }, [graph])

    const updateHighlight = () => {
        setHighlightNodes(highlightNodes);
        setHighlightLinks(highlightLinks);
    };

    const handleNodeHover = (node, graph: Graph) => {
        highlightNodes.clear();
        highlightLinks.clear();
        if (node) {
            highlightNodes.add(node);
            graph.forEachEdge(node.id, (edge, source, target) => {
                highlightLinks.add(data.links.find(link => link.id === edge));
                highlightNodes.add(target);
            });
            graph.forEachNeighbor(node.id, (neighbor, attributes) => {
                highlightNodes.add(data.nodes.find(node => node.id === neighbor));
            })
        }

        setHoverNode(node || null);
        updateHighlight();
    };

    const handleLinkHover = link => {
        highlightNodes.clear();
        highlightLinks.clear();

        if (link) {
            highlightLinks.add(link);
            highlightNodes.add(link.source);
            highlightNodes.add(link.target);
        }

        updateHighlight();
    };

    const paintRing = useCallback((node, ctx: CanvasRenderingContext2D) => {
        // add ring just for highlighted nodes
        ctx.fillStyle = '#ccc';
        ctx.fill();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.font = "5px Arial";
        ctx.fillText(node.id, node.x, node.y + NODE_R * 1.4 + 2);
        ctx.fillStyle = '#77c';
        ctx.fill();
        if (!highlightNodes.has(node)) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, NODE_R * 1.1, 0, 2 * Math.PI, false);
            ctx.fillStyle = '#ccc';
            ctx.fill();
            return
        }
        ctx.beginPath();
        ctx.arc(node.x, node.y, NODE_R * 1.4, 0, 2 * Math.PI, false);
        ctx.fillStyle = node === hoverNode ? 'red' : 'orange';
        ctx.fill();
    }, [hoverNode]);

    return <ForceGraph2D
        ref={fgRef}
        graphData={data}
        nodeRelSize={NODE_R}
        autoPauseRedraw={false}
        linkWidth={link => highlightLinks.has(link) ? 3 : 1}
        linkColor={link => highlightLinks.has(link) ? 'rgb(102, 102, 102)' : 'rgba(102, 102, 102, 0.3)'}
        linkDirectionalParticles={4}
        linkDirectionalParticleWidth={link => highlightLinks.has(link) ? 4 : 0}
        linkDirectionalParticleColor={() => 'red'}
        nodeCanvasObjectMode={node => 'before'}
        nodeCanvasObject={paintRing}
        onNodeHover={node => handleNodeHover(node, graph)}
        onLinkHover={handleLinkHover}
    />;
};
