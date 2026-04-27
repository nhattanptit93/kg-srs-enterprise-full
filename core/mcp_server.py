from mcp.server.fastmcp import FastMCP
import os

mcp = FastMCP("KG-SRS-Refine-Server")

def _parse_sections(content: str):
    lines = content.split('\n')
    sections = []
    current_header = None
    current_level = 0
    start_idx = 0
    
    for i, line in enumerate(lines):
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            if level > 0 and (len(line) == level or line[level] == ' '):
                if current_header is not None:
                    sections.append({
                        "header": current_header,
                        "level": current_level,
                        "start": start_idx,
                        "end": i
                    })
                current_header = line.strip()
                current_level = level
                start_idx = i
                
    if current_header is not None:
        sections.append({
            "header": current_header,
            "level": current_level,
            "start": start_idx,
            "end": len(lines)
        })
    return sections, lines

@mcp.tool()
def list_srs_sections(file_path: str) -> str:
    """Returns a list of all markdown headers in the SRS document. Use this to find the correct header to read or update."""
    if not os.path.exists(file_path):
        return f"File {file_path} not found."
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    sections, _ = _parse_sections(content)
    return "\n".join([s["header"] for s in sections])

@mcp.tool()
def get_srs_section(file_path: str, header: str) -> str:
    """Returns the content of a specific markdown section (including its sub-sections) from the SRS."""
    if not os.path.exists(file_path):
        return f"File {file_path} not found."
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    sections, lines = _parse_sections(content)
    
    target_idx = -1
    for i, s in enumerate(sections):
        if header.lower() in s["header"].lower():
            target_idx = i
            break
            
    if target_idx == -1:
        return f"Header containing '{header}' not found."
        
    target = sections[target_idx]
    
    end_idx = len(lines)
    for i in range(target_idx + 1, len(sections)):
        if sections[i]["level"] <= target["level"]:
            end_idx = sections[i]["start"]
            break
            
    return "\n".join(lines[target["start"]:end_idx])

@mcp.tool()
def update_srs_section(file_path: str, header: str, new_content: str) -> str:
    """Replaces a specific markdown section in the SRS with new_content. You must provide the FULL updated content for this section, including the header itself."""
    if not os.path.exists(file_path):
        return f"File {file_path} not found."
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    sections, lines = _parse_sections(content)
    
    target_idx = -1
    for i, s in enumerate(sections):
        if header.lower() in s["header"].lower():
            target_idx = i
            break
            
    if target_idx == -1:
        return f"Header containing '{header}' not found."
        
    target = sections[target_idx]
    
    end_idx = len(lines)
    for i in range(target_idx + 1, len(sections)):
        if sections[i]["level"] <= target["level"]:
            end_idx = sections[i]["start"]
            break
            
    new_lines = lines[:target["start"]] + new_content.split('\n') + lines[end_idx:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(new_lines))
        
    return f"Successfully updated section '{target['header']}' in {file_path}."

if __name__ == "__main__":
    mcp.run()
