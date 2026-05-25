import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Heading from '@theme/Heading';
import CodeBlock from '@theme/CodeBlock';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  const logoUrl = useBaseUrl('img/weaverlet-logo.png');
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <img
          src={logoUrl}
          alt="Weaverlet"
          className={styles.heroLogo}
        />
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.install}>
          <CodeBlock language="bash">pip install weaverlet</CodeBlock>
        </div>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/quickstart">
            Get started
          </Link>
          <Link
            className="button button--outline button--secondary button--lg"
            to="/docs/examples/">
            Examples
          </Link>
          <Link
            className="button button--outline button--secondary button--lg"
            href="https://github.com/observatoriogeo/weaverlet">
            GitHub
          </Link>
        </div>
      </div>
    </header>
  );
}

type FeatureRowProps = {
  title: string;
  body: ReactNode;
  code: string;
  dark?: boolean;
  language?: string;
};

function FeatureRow({title, body, code, dark, language = 'python'}: FeatureRowProps) {
  return (
    <section className={clsx(styles.featureRow, dark && styles.featureRowDark)}>
      <div className={clsx('container', styles.featureRowInner)}>
        <div className={styles.featureRowText}>
          <Heading as="h2" className={styles.featureRowTitle}>
            {title}
          </Heading>
          <p>{body}</p>
        </div>
        <div className={styles.featureRowCode}>
          <CodeBlock language={language}>{code}</CodeBlock>
        </div>
      </div>
    </section>
  );
}

const ROUTING_CODE = `from weaverlet import WeaverletApp, SimpleRouterComponent

router = SimpleRouterComponent(
    routes={
        "/":      HomePage(),
        "/about": AboutPage(),
        "/docs":  DocsPage(),
    },
    not_found_page_component=NotFoundPage(),
)
WeaverletApp(root_component=router).app.run()`;

const COMPONENT_CODE = `from weaverlet import WeaverletComponent, WeaverletApp, Identifier
from dash_extensions.enrich import Input, Output
from dash import html, dcc


class EchoComponent(WeaverletComponent):
    text_id = Identifier()
    echo_id = Identifier()

    def get_layout(self):
        return html.Div([
            dcc.Input(id=self.text_id),
            html.Div(id=self.echo_id),
        ])

    def register_callbacks(self, app):
        @app.callback(Output(self.echo_id, "children"),
                      Input(self.text_id, "value"))
        def echo(v): return v or ""`;

const IDENTIFIER_CODE = `class MyButton(WeaverletComponent):
    btn_id = Identifier()

    def get_layout(self):
        return html.Button("Click me", id=self.btn_id)


# Two instances, two unique Dash IDs, zero collisions.
btn_a = MyButton()
btn_b = MyButton()`;

const SIGNAL_CODE = `from weaverlet import SignalComponent, SignalOutput, SignalInput

# Producer: emit a payload dict to the signal.
@app.callback(SignalOutput(self.sig), Input(self.btn, "n_clicks"))
def emit(n):
    return {"clicks": n}


# Consumer: any component, anywhere in the DAG.
@app.callback(Output(self.label, "children"), SignalInput(self.sig))
def show(payload):
    return f"Got: {payload}"`;

const AUTH_CODE = `from weaverlet import AuthRouterComponent

router = AuthRouterComponent(
    routes={
        "/":      {"component": Dashboard(), "login_required": True},
        "/login": {"component": LoginPage(), "login_required": False},
    },
    not_found_page_component=NotFound(),
)`;

const LLM_URLS = `# Latest (tracks main):
https://cdn.jsdelivr.net/gh/observatoriogeo/weaverlet@main/ReadMe.LLM.md

# Pinned to v0.3.0:
https://cdn.jsdelivr.net/gh/observatoriogeo/weaverlet@v0.3.0/ReadMe.LLM.md`;

function FeatureCallout() {
  return (
    <section className={styles.callout}>
      <div className="container">
        <Heading as="h2">Get started</Heading>
        <div className={styles.calloutInstall}>
          <CodeBlock language="bash">pip install weaverlet</CodeBlock>
        </div>
        <div className={styles.buttons}>
          <Link className="button button--primary button--lg" to="/docs/quickstart">
            Quickstart
          </Link>
          <Link className="button button--primary button--lg" to="/docs/examples/">
            Examples
          </Link>
          <Link className="button button--primary button--lg" to="/docs/api/">
            API reference
          </Link>
          <Link
            className="button button--secondary button--lg"
            href="https://github.com/observatoriogeo/weaverlet">
            GitHub
          </Link>
          <Link
            className="button button--secondary button--lg"
            href="https://pypi.org/project/weaverlet/">
            PyPI
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout title={siteConfig.title} description={siteConfig.tagline}>
      <HomepageHeader />
      <main>
        <HomepageFeatures />
        <FeatureRow
          dark
          title="Multi-page apps without the wiring"
          body={
            <>
              Declare a route dict that maps paths to component instances.
              The router handles the rest: matching, 404 fallback, URL kwargs.
              Add <code>AuthRouterComponent</code> to gate routes behind
              Flask sessions.
            </>
          }
          code={ROUTING_CODE}
        />
        <FeatureRow
          title="Class-based encapsulation, server-side"
          body={
            <>
              Every UI block is a <code>WeaverletComponent</code> that owns its
              layout, callbacks, and IDs. Instantiate it twice and Dash treats
              the copies as independent. Same React mental model, pure Python.
            </>
          }
          code={COMPONENT_CODE}
        />
        <FeatureRow
          dark
          title="Auto-unique IDs that never collide"
          body={
            <>
              The <code>Identifier()</code> descriptor generates a unique Dash
              ID per instance, computed lazily and cached. You stop managing
              string IDs by hand and stop hitting{' '}
              <code>DuplicateIdError</code>.
            </>
          }
          code={IDENTIFIER_CODE}
        />
        <FeatureRow
          title="Signal-based events, not dcc.Store plumbing"
          body={
            <>
              <code>SignalComponent</code> plus typed adapters (
              <code>SignalInput</code>, <code>SignalOutput</code>,{' '}
              <code>SignalTrigger</code>) replace ad-hoc{' '}
              <code>dcc.Store</code> wiring as the cross-component event bus.
              Multiple producers and consumers work transparently thanks to{' '}
              <code>DashProxy</code> under the hood.
            </>
          }
          code={SIGNAL_CODE}
        />
        <FeatureRow
          dark
          title="Auth routing with Flask sessions"
          body={
            <>
              <code>AuthRouterComponent</code> gates routes behind{' '}
              <code>flask.session</code>. Unauthenticated visitors are
              redirected to the login route; on success, your login callback
              sets a session key and the user is bounced back to the page they
              were trying to reach.
            </>
          }
          code={AUTH_CODE}
        />
        <FeatureRow
          title="Built for LLM coding assistants"
          language="text"
          body={
            <>
              Weaverlet ships a <code>ReadMe.LLM.md</code> following the{' '}
              <a href="https://readmellm.github.io/">ReadMe.LLM methodology</a>
              {' '}plus an <code>llms.txt</code> at the repo root following the{' '}
              <a href="https://llmstxt.org/">llmstxt.org convention</a>. Drop a
              CDN URL into Claude, GPT, Codex, or Cursor and your assistant
              writes idiomatic Weaverlet code without guessing the API.{' '}
              <Link to="/docs/llm-assistants">
                See the full breakdown
              </Link>
              .
            </>
          }
          code={LLM_URLS}
        />
        <FeatureCallout />
      </main>
    </Layout>
  );
}
