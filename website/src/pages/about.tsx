import type {ReactNode} from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';

import styles from './about.module.css';

export default function About(): ReactNode {
  const centroGeoLogo = useBaseUrl('img/CentroGeo-CMX_Logo-V.png');
  const omLogo = useBaseUrl('img/Logo-OM-resized.png');

  return (
    <Layout title="About" description="About Weaverlet">
      <main className={styles.about}>
        <div className="container">
          <h1>About</h1>

          <div className={styles.affiliations}>
            <div className={styles.affiliationColumn}>
              <img
                src={centroGeoLogo}
                alt="CentroGeo"
                className={styles.affiliationLogo}
              />
              <h3>CentroGeo</h3>
              <p>
                Weaverlet is being developed at the{' '}
                <Link href="https://www.centrogeo.org.mx/">CentroGeo</Link>.
              </p>
            </div>

            <div className={styles.affiliationColumn}>
              <img
                src={omLogo}
                alt="Observatorio Metropolitano CentroGeo"
                className={styles.affiliationLogo}
              />
              <h3>Observatorio Metropolitano</h3>
              <p>
                Weaverlet is a research and tech product of the{' '}
                <Link href="https://observatoriogeo.mx">
                  Observatorio Metropolitano CentroGeo
                </Link>.
              </p>
            </div>
          </div>

          <h2>Author</h2>
          <p>
            Weaverlet is designed, developed, and maintained by{' '}
            <Link href="https://albertogarob.mx/">
              Dr. Alberto García Robledo
            </Link>{' '}
            at <Link href="https://www.centrogeo.org.mx/">CentroGeo</Link>,
            under <Link href="https://secihti.mx">SECIHTI</Link>'s{' '}
            <em>Investigadores por México</em> program.
          </p>
        </div>
      </main>
    </Layout>
  );
}
