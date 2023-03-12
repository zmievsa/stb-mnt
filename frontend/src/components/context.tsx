import { createContext } from 'preact'
import Graph from "graphology";

// interface for graph contexts
export interface GraphContext {
    graph?: Graph;
    saveGraph: (graph: Graph) => void;
    data: { nodes: any[], links: any[] };
    setData: (data: any) => void;
    graphVersion: number;
    setGraphVersion: (version: number) => void;
}

export const GraphContext = createContext<GraphContext>({
    saveGraph: () => { },
    data: { nodes: [], links: [] },
    setData: () => { },
    graphVersion: 0,
    setGraphVersion: () => { },
});

