import os

# Create a configuration dictionary for OCLC credentials
# Gets values from environment variables if they exist, otherwise sets to None
OCLC_CONFIG = {
    'POST45_OCLC_CLIENT_ID': os.environ.get('OCLC_CLIENT', None),
    'POST45_OCLC_SECRET': os.environ.get('OCLC_SECRET', None)
}

# You can also create this as a function if you need to refresh the values
def get_oclc_config():
    """
    Returns a dictionary with OCLC configuration.
    Gets values from environment variables OCLC_CLIENT and OCLC_SECRET if they exist,
    otherwise returns None for those keys.
    """
    return {
        'POST45_OCLC_CLIENT_ID': os.environ.get('OCLC_CLIENT', None),
        'POST45_OCLC_SECRET': os.environ.get('OCLC_SECRET', None)
    }

# Example usage:
if __name__ == "__main__":
    # Print the configuration
    config = get_oclc_config()
    print("OCLC Configuration:")
    print(f"  POST45_OCLC_CLIENT_ID: {'[SET]' if config['POST45_OCLC_CLIENT_ID'] else '[NOT SET]'}")
    print(f"  POST45_OCLC_SECRET: {'[SET]' if config['POST45_OCLC_SECRET'] else '[NOT SET]'}")
    
    # You can also use the module-level dictionary
    print("\nUsing module-level OCLC_CONFIG:")
    print(f"  POST45_OCLC_CLIENT_ID: {OCLC_CONFIG['POST45_OCLC_CLIENT_ID']}")
    print(f"  POST45_OCLC_SECRET: {'***' if OCLC_CONFIG['POST45_OCLC_SECRET'] else None}")