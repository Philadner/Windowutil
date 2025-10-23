def run_command_chain(registry, window, chain):
    current = window
    for cmd in chain:
        if cmd not in registry:
            print(f"Unknown command: {cmd}")
            continue
        current = registry[cmd]["instance"].main(current)
    return current
