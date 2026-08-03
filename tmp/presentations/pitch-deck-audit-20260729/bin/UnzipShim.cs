using System;
using System.IO;
using System.IO.Compression;

internal static class UnzipShim
{
    private static int Main(string[] args)
    {
        try
        {
            if (args.Length == 2 && args[0] == "-Z1")
            {
                using (var archive = ZipFile.OpenRead(args[1]))
                {
                    foreach (var entry in archive.Entries)
                    {
                        Console.Out.WriteLine(entry.FullName);
                    }
                }
                return 0;
            }

            if (args.Length == 3 && args[0] == "-p")
            {
                using (var archive = ZipFile.OpenRead(args[1]))
                {
                    var entry = archive.GetEntry(args[2]);
                    if (entry == null)
                    {
                        Console.Error.WriteLine("Archive entry not found: " + args[2]);
                        return 3;
                    }

                    using (var input = entry.Open())
                    using (var output = Console.OpenStandardOutput())
                    {
                        input.CopyTo(output);
                    }
                }
                return 0;
            }

            Console.Error.WriteLine("Unsupported unzip compatibility arguments.");
            return 2;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine(error.Message);
            return 1;
        }
    }
}
