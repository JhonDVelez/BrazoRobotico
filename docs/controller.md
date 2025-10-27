# Controller

::: src.data.controller
    handler: python
    options:
        show_source: false
        show_root_heading: false
        show_root_toc_entry: false
        filters:
            - "!DataFlow"   # evita duplicar la clase

## DataFlow
::: src.data.controller.DataFlow
    handler: python
    options:
        members:
            - request_objective_data
            - update_simulation
            - update_robot
        show_source: false
        show_root_heading: false
        show_bases: true
        show_root_toc_entry: false