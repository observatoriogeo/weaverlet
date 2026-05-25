import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Weaverlet',
  tagline: 'OOP for Plotly Dash. Make your dashboards composable.',
  favicon: 'img/weaverlet-logo.png',

  future: {
    v4: true,
  },

  url: 'https://weaverlet.observatoriogeo.mx',
  baseUrl: '/',

  organizationName: 'observatoriogeo',
  projectName: 'weaverlet',

  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/observatoriogeo/weaverlet/edit/main/website/',
          lastVersion: '0.3.1',
          // The "last version" serves at /docs/ (empty path) by default;
          // the unreleased "next" version (whatever lives in docs/) serves
          // at /docs/next/ once a second version is snapshotted.
          versions: {
            '0.3.1': {label: '0.3.1'},
          },
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themes: [
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {
        hashed: true,
        language: ['en'],
        docsRouteBasePath: '/docs',
        indexBlog: false,
        highlightSearchTermsOnTargetPage: true,
      },
    ],
  ],

  themeConfig: {
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Weaverlet',
      logo: {
        alt: 'Weaverlet',
        src: 'img/weaverlet-logo.png',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docs',
          position: 'left',
          label: 'Docs',
        },
        {
          // Trailing slash is load-bearing: without it, React Router pushes
          // /docs/examples (no slash) on click, and any relative MDX link
          // on that page resolves against the no-slash form and drops the
          // /examples/ segment. Same fix applies to /docs/api below.
          to: '/docs/examples/',
          label: 'Examples',
          position: 'left',
        },
        {
          to: '/docs/api/',
          label: 'Reference',
          position: 'left',
        },
        {
          to: '/about',
          label: 'About',
          position: 'left',
        },
        {type: 'docsVersionDropdown', position: 'right'},
        {
          href: 'https://pypi.org/project/weaverlet/',
          label: 'PyPI',
          position: 'right',
        },
        {
          href: 'https://github.com/observatoriogeo/weaverlet',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            // Trailing slashes on directory-style targets only (api/) —
            // single-page docs like installation, quickstart, changelog
            // are not directory indexes so they don't need it.
            {label: 'Getting started', to: '/docs/installation'},
            {label: 'Quickstart', to: '/docs/quickstart'},
            {label: 'Reference', to: '/docs/api/'},
            {label: 'Changelog', to: '/docs/changelog'},
          ],
        },
        {
          title: 'Project',
          items: [
            {label: 'GitHub', href: 'https://github.com/observatoriogeo/weaverlet'},
            {label: 'PyPI', href: 'https://pypi.org/project/weaverlet/'},
            {label: 'Issues', href: 'https://github.com/observatoriogeo/weaverlet/issues'},
          ],
        },
        {
          title: 'Authors',
          items: [
            {label: 'CentroGeo', href: 'https://www.centrogeo.org.mx/'},
            {label: 'Observatorio Metropolitano CentroGeo', href: 'https://observatoriogeo.mx'},
            {label: 'SECIHTI', href: 'https://secihti.mx'},
          ],
        },
      ],
      copyright: `Copyright © 2026 Centro de Investigación en Ciencias de Información Geoespacial. MIT licensed.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['python', 'bash'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
