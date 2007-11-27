def gigs_to_kb(val_in_gigs)
  return val_in_gigs.to_i * 1024 * 1024
end
 
def kb_to_gigs(val_in_kb)
  return val_in_kb.to_i / 1024 / 1024
end
