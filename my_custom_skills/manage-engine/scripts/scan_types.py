from manage_engine_api import AppManagerClient, DEFAULT_URL, DEFAULT_API_KEY

def scan_all_types():
    client = AppManagerClient(DEFAULT_URL, DEFAULT_API_KEY)
    
    print("--- Scanning all resource types ---")
    data = client.list_monitors()
    
    if data and 'response' in data and 'result' in data['response']:
        monitors = data['response']['result']
        
        # Count types
        type_counts = {}
        for m in monitors:
            m_type = m.get('TYPE', 'Unknown')
            if m_type in type_counts:
                type_counts[m_type] += 1
            else:
                type_counts[m_type] = 1
        
        print("\n[Resource Types in System]")
        for t, count in sorted(type_counts.items(), key=lambda item: item[1], reverse=True):
            print(" - " + t + ": " + str(count))
            
        # Check for groups
        print("\n[Potential Groups]")
        found = False
        for m in monitors:
            m_name = m.get('DISPLAYNAME', '')
            m_type = m.get('TYPE', '')
            if 'Group' in m_type or 'group' in m_name.lower():
                print(" > [" + m.get('RESOURCEID') + "] " + m_name + " (" + m_type + ")")
                found = True
        
        if not found:
            print("No resources with 'Group' in name or type found.")
            
    else:
        print("API No Response.")

if __name__ == "__main__":
    scan_all_types()