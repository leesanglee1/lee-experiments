flowchart TD
    A[Start] --> B{Is the API complex?}
    B -->|Yes| C{Need to simplify interface?}
    B -->|No| D{High security requirements?}
    
    C -->|Yes| E[Use Wrapper Service]
    C -->|No| D
    
    D -->|Yes| F{Need additional auth?}
    D -->|No| G{Significant data transformation?}
    
    F -->|Yes| E
    F -->|No| G
    
    G -->|Yes| E
    G -->|No| H{Performance critical?}
    
    H -->|Yes| I{Can wrapper improve performance?}
    H -->|No| J{Versioning issues?}
    
    I -->|Yes| E
    I -->|No| K[Use API Directly]
    
    J -->|Yes| E
    J -->|No| K
    
    E --> L[End]
    K --> L
