<p align="center">
  <img src="FullLogo_Transparent_NoBuffer.png" width="375" height="275" title="Logo">
</p>

# Weaverlet

Weaverlet is a slim, server-side, component-driven framework developed by the [Observatorio Metropolitano CentroGeo](https://observatoriogeo.mx) designed to simplify the building of multi-page web dashboard applications. Built on top of the [Plotly Dash framework](https://dash.plotly.com/), Weaverlet allows developers to create complex dashboard applications entirely in Python, without the need for JavaScript, HTML, CSS, or templating languages.

Weaverlet is designed around the concept of the Weaverlet Component: a class that encapsulates the complexities of layout and callbacks of one or more Dash components, which together perform a single high-level user interface function, presenting them as a self-contained, composable, and reusable UI component.

A complete visualization application can be "composed" from nested Weaverlet Components that together create a component hierarchy. It is possible to leverage any existing Dash component to build new Weaverlet Components. 

Moreover, Weaverlet Components can communicate with other components within the hierarchy through signals and share a context to store and convey data.

Weaverlet is specifically designed to cater to the following user groups:

* Data scientists seeking to build comprehensive data visualization applications consisting of multiple dashboards.
* Python developers proficient in Dash, aiming to develop data visualization applications using components that can be seamlessly reused across different applications.
* JavaScript developers accustomed to the component-based programming approach employed by popular frameworks such as React.

## Key Features

- **Multi-Page Support**: Seamlessly manage multi-page Dash web applications.
- **Component-Based Design**: Utilize Weaverlet Components, which follow a component-based paradigm similar to popular front-end frameworks, but are entirely managed through a Python OOP interface.
- **Inter-Component Communication**: Components can communicate with parent, child, and root components within the application.
- **Session-Based Authentication**: Implement session-based authentication to manage user sessions within your dashboard applications.
- **Shared Context**: Maintain a shared context across all components in the Weaverlet Component Directed Acyclic Graph (DAG), enhancing consistency and manageability.

## Getting Started

To get started with Weaverlet, you can install the package using pip:

```bash
pip install weaverlet
```

Here's a simple example demonstrating how to encapsulate a basic Dash dashboard within a Weaverlet component:

```python
from weaverlet.base import WeaverletComponent, WeaverletApp, Identifier
from dash.dependencies import Input, Output
from dash import html, dcc


class EchoComponent(WeaverletComponent):

    text_input_id = Identifier()    
    echo_div_id = Identifier()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self):
        return html.Div([
            dcc.Input(id=self.text_input_id,
                      type='text'),
            html.Div(id=self.echo_div_id)
        ])

    def register_callbacks(self, app):
        @app.callback(
            Output(self.echo_div_id, 'children'),
            Input(self.text_input_id, 'value')
        )
        def update_echo_div(text_value):
            return f'{text_value}'


greeting_component = EchoComponent()
wapp = WeaverletApp(root_component=greeting_component)
wapp.app.run()
```

Here’s a simple example to show how to set up a basic Weaverlet application made of two dashboards (pages):

```python
from weaverlet.base import WeaverletComponent, WeaverletApp
from weaverlet.components import SimpleRouterComponent
from dash import html


class PageAComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, pathname, hash, href, search):
        return html.Div(f'hello from Page A!')


class PageBComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, pathname, hash, href, search):
        return html.Div(f'hello from Page B!')


class PageNotFoundComponent(WeaverletComponent):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get_layout(self, pathname):
        return html.Div(f'Page not found!')


page_a_component = PageAComponent()
page_b_component = PageBComponent()
not_found_page_component = PageNotFoundComponent()

routes = {
    '/': page_a_component,
    '/page_a': page_a_component,
    '/page_b': page_b_component
}
router_component = SimpleRouterComponent(
    routes=routes,
    not_found_page_component=not_found_page_component
)

wapp = WeaverletApp(root_component=router_component)
wapp.app.run()
```

For more detailed usage, please refer to the examples folder.

## License

Weaverlet is open-source software [licensed under the MIT license](LICENSE).

## Support

If you have any questions or issues, please open an issue on the GitHub repository or contact us.

