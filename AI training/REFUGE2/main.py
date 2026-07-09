import argparse
import train
import evaluate

def main():
    
    parser = argparse.ArgumentParser(description="Glavni pokretač Glaukom Pipeline-a")
    
    parser.add_argument(
        "--mode", 
        type=str, 
        default="all", 
        choices=["train", "evaluate", "all"],
        help="Mod rada: 'train' za samo trening, 'evaluate' za samo evaluaciju, 'all' za oba odjednom."
    )
    
    args = parser.parse_args()

    if args.mode == "train":
        print("\n=== POKRETANJE SAMO TRENING MODULA ===")
        train.main()
        
    elif args.mode == "evaluate":
        print("\n=== POKRETANJE SAMO EVALUACIJE MODULA ===")
        evaluate.main()
        
    elif args.mode == "all":
        print("\n==================================================")
        print("=== ZAPOČINJANJE KOMPLETNOG DIAGNOSTIČKOG PIPELINE-A ===")
        print("==================================================")
        
        
        print("\n[KORAK 1/2] Pokretanje treninga mreže...")
        train.main()
        
        print("\n[INFO] Trening uspešno završen. Prelazak na evaluaciju...")
        print("--------------------------------------------------")
        
        
        print("\n[KORAK 2/2] Pokretanje evaluacije i ekstrakcije kliničkih parametara...")
        evaluate.main()
        
        print("\n==================================================")
        print("=== PIPELINE USPEŠNO ZAVRŠIO SVE KORAKE! ===")
        print("==================================================")

if __name__ == "__main__":
    main()