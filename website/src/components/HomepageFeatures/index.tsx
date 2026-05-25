import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  description: ReactNode;
  link?: {to: string; label: string};
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Class-based encapsulation',
    description: (
      <>
        Layout, callbacks, state, and IDs live together in one class.
        Instantiate twice for two independent copies that don't step on each other.
      </>
    ),
    link: {to: '/docs/concepts/components', label: 'Components →'},
  },
  {
    title: 'Auto-unique IDs',
    description: (
      <>
        The <code>Identifier()</code> descriptor generates a unique Dash ID per
        instance. No more managing string IDs by hand or hitting{' '}
        <code>DuplicateIdError</code>.
      </>
    ),
    link: {to: '/docs/api/identifier', label: 'Identifier →'},
  },
  {
    title: 'Multi-page routing',
    description: (
      <>
        <code>SimpleRouterComponent</code> maps URL paths to component
        instances. Built-in 404 handling, optional auth gating, clean
        composition. No filesystem conventions to learn.
      </>
    ),
    link: {to: '/docs/routing/simple-router', label: 'Routing →'},
  },
];

function Feature({title, description, link}: FeatureItem) {
  return (
    <div className={clsx('col col--4', styles.feature)}>
      <div className="padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
        {link && (
          <Link to={link.to} className={styles.featureLink}>
            {link.label}
          </Link>
        )}
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
