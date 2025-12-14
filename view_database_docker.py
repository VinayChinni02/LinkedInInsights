"""
View database from inside Docker container (most reliable).
This script should be run inside the Docker container or use docker exec.
"""
import subprocess
import sys

def view_from_docker():
    """View database using docker exec."""
    print("Viewing MongoDB database from Docker container...")
    print("=" * 80)
    
    commands = [
        ("db.pages.countDocuments()", "Total Pages"),
        ("db.posts.countDocuments()", "Total Posts"),
        ("db.users.countDocuments()", "Total People"),
        ("db.comments.countDocuments()", "Total Comments"),
    ]
    
    for cmd, label in commands:
        try:
            result = subprocess.run(
                ["docker", "exec", "deepsolv-mongodb-1", "mongosh", "linkedin_insights", "--eval", cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Extract number from output
                output = result.stdout.strip()
                # Find number in output
                import re
                numbers = re.findall(r'\d+', output)
                if numbers:
                    print(f"{label}: {numbers[-1]}")
                else:
                    print(f"{label}: {output}")
            else:
                print(f"{label}: Error - {result.stderr}")
        except Exception as e:
            print(f"{label}: Error - {e}")
    
    print("\n" + "=" * 80)
    print("To view full data, use:")
    print("  docker exec deepsolv-mongodb-1 mongosh linkedin_insights")
    print("\nThen run:")
    print("  db.pages.find().pretty()")
    print("  db.posts.find().pretty()")
    print("  db.users.find().pretty()")

if __name__ == "__main__":
    view_from_docker()

