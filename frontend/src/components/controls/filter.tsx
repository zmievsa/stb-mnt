import { useState, useEffect, useContext } from 'preact/hooks'
import { GraphContext } from '../context'



export const Filter = ({ showNodes, setShowNodes }) => {
    const [nodes, setNodes] = useState([]);
    const { graph, graphVersion, saveGraph } = useContext(GraphContext);


    const handleChange = event => {
        if (!graph) {
            return
        }
        const { value, checked } = event.target;
        graph.setNodeAttribute(value, 'hidden', !checked)
        saveGraph(graph);
    };

    useEffect(() => {
        if (!graph) {
            return;
        }
        setNodes(graph.nodes());
    }, [graphVersion]);




    return (
        <div className="flex-1 flex-col">
            <h2>Filter</h2>
            {nodes.map(node => (
                <div >
                    <label key={node}>
                        <input
                            type="checkbox"
                            value={node}
                            checked={!graph.getNodeAttribute(node, 'hidden')}
                            onChange={handleChange}
                            className="mr-2"
                        />
                        {node}
                    </label>
                </div>
            ))}
        </div>
    );
}
