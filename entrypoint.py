import sys, os, re, uuid

dockerfile = sys.argv[1]
fail_on_unpinned = sys.argv[2].upper()

def is_unpinned(image_ref):
    if '@' in image_ref:
        return False
        
    last_slash_idx = image_ref.rfind('/')
    name_and_tag = image_ref[last_slash_idx:] if last_slash_idx != -1 else image_ref
    
    if ':' in name_and_tag:
        tag = name_and_tag.split(':')[-1]
        if tag.lower() == 'latest':
            return True
        return False
    else:
        return True
    

try:
    unpinned_images = []
    report_lines = []
    defined_stages = set()

    if not os.path.isfile(dockerfile):
        print("Docker File Not Found...")
        sys.exit(1)

    with open(dockerfile, "r", encoding="utf-8-sig") as file:
        from_regex = re.compile(r'^\s*FROM\s+(?:--[^\s]+\s+)*([^\s]+)(?:\s+[aA][sS]\s+([^\s]+))?', re.IGNORECASE)
        
        for line_num, line in enumerate(file, 1):
            clean_line = line.split('#')[0].strip()
            if not clean_line:
                continue
            
            match = from_regex.match(clean_line)
            if match:
                image_ref = match.group(1)
                stage_alias = match.group(2)
                if image_ref.lower() in defined_stages:
                    pass
                elif image_ref.lower() == 'scratch':
                    pass
                elif is_unpinned(image_ref):
                    unpinned_images.append((line_num, image_ref, clean_line))
                    report_lines.append(f"Line {line_num}: {clean_line} -> Image '{image_ref}' is unpinned.")
                    
                if stage_alias:
                    defined_stages.add(stage_alias.lower())
            
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        delimiter = f"EOF_{uuid.uuid4().hex}"
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"unpinned-count={len(unpinned_images)}\n")
            f.write(f"report<<{delimiter}\n")
            f.write("\n".join(report_lines) + "\n")
            f.write(f"{delimiter}\n")
            
    
    if unpinned_images:
        print(f"❌ Found {len(unpinned_images)} unpinned base image(s) in '{dockerfile}':\n")
        for line_num, img, line in unpinned_images:
            print(f"  Line {line_num}: {line}")
            print(f"    -> Warning: Image '{img}' is unpinned.\n")
            
        if fail_on_unpinned == "TRUE" or fail_on_unpinned == "YES":
            sys.exit(1)
    else:
        print(f"✅ All base images in '{dockerfile}' are properly pinned!")
        sys.exit(0)

except FileNotFoundError:
    print(f"Error: File '{dockerfile}' not found.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error reading file: {e}", file=sys.stderr)
    sys.exit(1)