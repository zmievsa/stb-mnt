import { useState, useEffect } from 'preact/hooks'

import Graph from "graphology";
import { random } from "graphology-layout";
import jsonDependencies from "../dependencies.json";
import { Filter } from './components/controls/filter'
import { Settings } from './components/controls/settings'
import { GraphRender } from './components/graphRender'
import { GraphContainer, LoadGraph } from './components/graph'
import { selectNode, resetGraph } from './utils'
import { GraphContext } from './components/context';



export function App() {

    const [showNodes, setShowNodes] = useState({});

    return (
        <GraphContainer >
            <LoadGraph jsonDependencies={new Map(Object.entries(jsonDependencies))} />
            <GraphRender />
            <Settings>
                <Filter showNodes={showNodes} setShowNodes={setShowNodes} />
            </Settings>
        </GraphContainer>
    );
};
