import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docs: [
    'intro',
    {
      type: 'category',
      label: 'Getting started',
      collapsed: false,
      items: ['installation', 'quickstart', 'first-app'],
    },
    'comparisons',
    'llm-assistants',
    {
      type: 'category',
      label: 'Core concepts',
      items: [
        'concepts/components',
        'concepts/app-lifecycle',
        'concepts/dag-composition',
        'concepts/context',
        {
          type: 'category',
          label: 'Signals',
          items: [
            'signals/overview',
            'signals/input-output',
            'signals/trigger',
            'signals/chains',
            'signals/store-component',
            'signals/serverside',
          ],
        },
        {
          type: 'category',
          label: 'Routing',
          items: [
            'routing/simple-router',
            'routing/keep-mounted',
            'routing/auth-router',
            'routing/redirects',
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Examples',
      link: {type: 'doc', id: 'examples/index'},
      items: [
        'examples/hello-world',
        'examples/echo',
        'examples/greeting',
        'examples/router',
        'examples/auth-router',
        'examples/redirect',
        'examples/signal-input',
        'examples/signal-trigger',
        'examples/signal-chain',
        'examples/div-signal',
        'examples/dbc-single',
        'examples/dbc-multipage',
        'examples/dbc-modal',
        'examples/dmc-keep-mounted',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      link: {type: 'doc', id: 'api/index'},
      items: [
        'api/weaverlet-component',
        'api/weaverlet-app',
        'api/identifier',
        'api/simple-router',
        'api/auth-router',
        'api/redirect',
        'api/signal',
        'api/div-signal',
        'api/store',
        'api/empty-layout',
        'api/signal-adapters',
        'api/detached-ref',
        'api/exceptions',
      ],
    },
    'compatibility',
    'changelog',
    'credits',
  ],
};

export default sidebars;
