import { useState, useEffect } from 'preact/hooks';

import Graph from 'graphology';
import { random } from 'graphology-layout';
import { Filter } from './components/controls/filter';
import { Settings } from './components/controls/settings';
import dependencies from '../default_dependencies.json';
import { GraphRender } from './components/graphRender';
import { GraphContainer, LoadGraph } from './components/graph';
import { selectNode, resetGraph } from './utils';
import { GraphContext } from './components/context';

export function App() {
  const [jsonInput, setJsonInput] = useState(JSON.stringify(dependencies, null, 2));
  const [jsonDependencies, setJsonDependencies] = useState(new Map());
  const [showNodes, setShowNodes] = useState({});
  const [dependenciesLoaded, setDependenciesLoaded] = useState(false);

  const handleJsonInputChange = (event) => {
    setJsonInput(event.target.value);
    setDependenciesLoaded(false);
  };

  useEffect(() => {
    if (jsonInput && !dependenciesLoaded) {
      try {
        const jsonData = JSON.parse(jsonInput);
        setJsonDependencies(new Map(Object.entries(jsonData)));
        setDependenciesLoaded(true);
      } catch (error) {
        console.error('Invalid JSON input', error);
      }
    }
  }, [jsonInput, dependenciesLoaded]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minHeight: '100vh' }}>
      <GraphContainer>
        <div style={{ width: '50%', marginBottom: '1rem' }}>
          <textarea
            placeholder="Enter JSON here"
            value={jsonInput}
            onChange={handleJsonInputChange}
            style={{ width: '100%', minHeight: '100px', resize: 'none' }}
          />
        </div>
        {dependenciesLoaded && (
          <>
            <LoadGraph jsonDependencies={jsonDependencies} />
            <GraphRender />
            <Settings>
              <Filter showNodes={showNodes} setShowNodes={setShowNodes} />
            </Settings>
          </>
        )}
      </GraphContainer>
    </div>
  );
};
