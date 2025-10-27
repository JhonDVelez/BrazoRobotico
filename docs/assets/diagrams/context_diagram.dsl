workspace "Name" "Description"

    !identifiers hierarchical

    model {
        u = person "Usuario"
        ss = softwareSystem "Sistema De Software" {
            gui = container "Interfaz Grafica"
            be = container "Backend"{
                tags "Backend"
            }
            gr = container "Graficadora"
        }
        rb = person "Robot" {
            tags "Robot"
        }
        
        u -> ss.gui "Comandos"
        ss.gui -> ss.be "Datos Crudos"
        ss.be -> ss.gr "Coordenadas de puntos"
        ss.be -> rb "Angulos Objetivos"
        
        ss.gr -> ss.gui "Vista De Señales"
    }

    views {
        systemContext ss "Diagram1" {
            include *
            autolayout lr
        }

        container ss "Diagram2" {
            include *
            autolayout lr
        }

        styles {
            element "Element" {
                color #0773af
                stroke #0773af
                strokeWidth 7
                shape roundedbox
            }
            element "Person" {
                shape person
            }
            element "Robot"{
                shape robot
            }
            element "Backend"{
                shape server
            }
            element "Database" {
                shape cylinder
            }
            element "Boundary" {
                strokeWidth 5
            }
            relationship "Relationship" {
                thickness 4
            }
        }
    }

}